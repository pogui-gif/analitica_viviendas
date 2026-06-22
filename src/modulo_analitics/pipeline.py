"""
Orquestador del pipeline ETL + Analitica (fases 1-3 del proyecto).

Conecta los modulos ya existentes en un flujo unico y reproducible:

    [fuente]  ->  extract  ->  clean  ->  dedup  ->  stats  ->  exports (BI + IA)

Fuentes soportadas (parametro `fuente`):
    "datalake" : lee el HTML renderizado mas reciente del datalake (Drive).
    "scrape"   : scrapea en vivo con Playwright y luego procesa.
    "sample"   : usa el dataset de muestra para correr offline.
    Path/str   : ruta directa a un archivo .html o .csv.

El resultado es un objeto ResultadoPipeline con el DataFrame limpio y todas las
tablas analiticas, ademas de los archivos persistidos en data/processed/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from . import clean, config, drive, extract, fetch, stats


# ---------------------------------------------------------------------------
# Estructura de resultado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoPipeline:
    df: pd.DataFrame                              # tabla de hechos limpia
    tablas: Dict[str, pd.DataFrame] = field(default_factory=dict)
    resumen_mercado: Dict[str, Any] = field(default_factory=dict)
    fuente: str = ""
    archivos: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 1. Carga / Extraccion -> DataFrame crudo
# ---------------------------------------------------------------------------
def _cargar_dataframe(fuente: Union[str, Path]) -> pd.DataFrame:
    """Resuelve la fuente y devuelve un DataFrame CRUDO (pre-clean).

    Para CSV ya procesados (sample) devolvemos el DataFrame tal cual; el flag
    `_ya_limpio` en los atributos indica que no hay que volver a limpiar.
    """
    # Rutas directas
    if isinstance(fuente, Path) or (isinstance(fuente, str) and fuente.endswith((".html", ".csv"))):
        ruta = Path(fuente)
        if not ruta.exists():
            raise FileNotFoundError(f"No existe la fuente indicada: {ruta}")
        if ruta.suffix == ".csv":
            df = pd.read_csv(ruta)
            df.attrs["_ya_limpio"] = True
            return df
        return extract.extraer_datos(fetch.leer_html(ruta))

    if fuente == "sample":
        ruta = config.SAMPLE_DIR / "sample_inmuebles.csv"
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontro el dataset de muestra en {ruta}. "
                "Genera uno o usa fuente='datalake'."
            )
        df = pd.read_csv(ruta)
        df.attrs["_ya_limpio"] = True
        return df

    if fuente == "scrape":
        ruta = fetch.scrapear()
        return extract.extraer_datos(fetch.leer_html(ruta))

    if fuente == "drive":
        drive.sincronizar_datalake()
        return _cargar_datalake()

    if fuente == "datalake":
        return _cargar_datalake()

    raise ValueError(f"Fuente no reconocida: {fuente!r}")


def _normalizar_csv_crudo(df: pd.DataFrame) -> pd.DataFrame:
    """Marca un CSV del datalake como crudo (necesita clean) o ya limpio.

    Los CSV del datalake (`datos/dataframes/.../pagina_N.csv`) tienen 11 columnas
    nombradas 0..10 = salida cruda de extract -> requieren clean.limpiar_datos.
    Un CSV con >=13 columnas se asume ya limpio (incluye id/link).
    """
    if list(df.columns[:1]) == ["Unnamed: 0"]:
        df = df.drop(columns=["Unnamed: 0"])
    df.attrs["_ya_limpio"] = df.shape[1] >= len(config.COLUMNAS_LIMPIAS)
    return df


def _cargar_datalake() -> pd.DataFrame:
    """Carga la particion mas reciente del datalake (multi-pagina).

    Prioriza el HTML crudo (pipeline completo extract+clean). Si no hay HTML,
    usa los CSV pre-extraidos. Concatena todas las paginas de la particion.
    """
    htmls = fetch.localizar_htmls_recientes()
    if htmls:
        print(f"Leyendo {len(htmls)} pagina(s) HTML del datalake "
              f"(particion: {htmls[0].parent.name}).")
        partes = [extract.extraer_datos(fetch.leer_html(h)) for h in htmls]
        return pd.concat(partes, ignore_index=True)

    csvs = fetch.localizar_csvs_recientes()
    if csvs:
        print(f"No hay HTML; usando {len(csvs)} CSV pre-extraido(s) del datalake.")
        df = pd.concat([pd.read_csv(c) for c in csvs], ignore_index=True)
        return _normalizar_csv_crudo(df)

    raise FileNotFoundError(
        f"No hay HTML ni CSV en el datalake ({config.DATALAKE_DIR}). "
        "Verifica DRIVE_URL/DATALAKE_DIR o usa fuente='scrape'/'sample'."
    )


# ---------------------------------------------------------------------------
# 2. Limpieza + deduplicacion
# ---------------------------------------------------------------------------
def _preparar(df: pd.DataFrame, control_calidad: bool = True) -> pd.DataFrame:
    """Aplica clean.limpiar_datos (si hace falta), dedup y control de calidad."""
    if not df.attrs.get("_ya_limpio", False):
        df = clean.limpiar_datos(df)

    antes = len(df)
    if "id" in df.columns:
        df = df.drop_duplicates(subset="id").reset_index(drop=True)
    quitados = antes - len(df)
    if quitados:
        print(f"Deduplicacion: {quitados} publicaciones repetidas eliminadas.")

    if control_calidad:
        df = aplicar_control_calidad(df)
    return df


def aplicar_control_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """Sanea el dataset para el analisis de ARRIENDO, reportando cada exclusion.

    1) Excluye listados de venta (precio de venta, no canon de arriendo).
    2) Aplica cotas de dominio [PRECIO_MIN, PRECIO_MAX] sobre el canon.

    Configurable via config (FILTRAR_VENTA, FILTRAR_OUTLIERS, PRECIO_MIN/MAX).
    """
    df = df.copy()
    n0 = len(df)

    if config.FILTRAR_VENTA and "servicio" in df.columns:
        es_venta = df["servicio"].str.contains("venta", case=False, na=False)
        if es_venta.any():
            print(f"  [calidad] {int(es_venta.sum())} listados con 'Venta' excluidos "
                  "(muestran precio de venta, no canon).")
            df = df[~es_venta]

    if config.FILTRAR_OUTLIERS:
        precio = pd.to_numeric(df["precio"], errors="coerce")
        fuera = (precio < config.PRECIO_MIN) | (precio > config.PRECIO_MAX)
        if fuera.any():
            print(f"  [calidad] {int(fuera.sum())} inmuebles fuera de rango "
                  f"[${config.PRECIO_MIN:,.0f}–${config.PRECIO_MAX:,.0f}] excluidos.")
            df = df[~fuera]

    df = df.reset_index(drop=True)
    if len(df) != n0:
        print(f"  [calidad] Dataset saneado: {n0} -> {len(df)} inmuebles.")
    return df


# ---------------------------------------------------------------------------
# 3. Analitica: ejecutar todas las funciones de stats de forma robusta
# ---------------------------------------------------------------------------
def calcular_estadisticas(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Corre todo stats.py y devuelve un diccionario de tablas analiticas.

    Cada calculo va aislado: si uno falla (p.ej. qcut con pocos datos) no tumba
    el resto del pipeline; se registra una advertencia.
    """
    tablas: Dict[str, pd.DataFrame] = {}

    def _intentar(nombre: str, fn):
        try:
            tablas[nombre] = fn()
        except Exception as exc:  # noqa: BLE001  (queremos resiliencia aqui)
            print(f"  [advertencia] No se pudo calcular '{nombre}': {exc}")

    _intentar("extremos_precio", lambda: stats.obtener_extremos_precio(df))

    def _distribucion():
        total, tabla = stats.distribucion_geografica(df)
        tabla = tabla.reset_index().rename(columns={"index": "barrio", "barrio": "barrio"})
        tabla.attrs["total_barrios"] = total
        return tabla
    _intentar("distribucion_geografica", _distribucion)

    _intentar("tendencia_central", lambda: stats.tendencia_central_precios(df).reset_index())

    def _valor_m2():
        df_calc, ranking = stats.valorizacion_metro_cuadrado(df)
        tablas["fact_con_valor_m2"] = df_calc
        return ranking
    _intentar("ranking_valor_m2", _valor_m2)

    _intentar("matriz_correlacion", lambda: stats.determinantes_precio(df).reset_index().rename(columns={"index": "variable"}))

    def _adicional():
        p_banos, p_habit, control = stats.analisis_adicional(df)
        tablas["precio_por_banos"] = p_banos
        tablas["precio_por_habitacion"] = p_habit
        return control
    _intentar("control_barrio_similares", _adicional)

    def _impacto():
        i_banos, i_habit, i_parq, i_area = stats.impacto_caracteristicas(df)
        tablas["impacto_habitaciones"] = i_habit
        tablas["impacto_parqueaderos"] = i_parq
        tablas["impacto_area"] = i_area
        return i_banos
    _intentar("impacto_banos", _impacto)

    return tablas


# ---------------------------------------------------------------------------
# 4. Resumen serializable para el agente de IA
# ---------------------------------------------------------------------------
def construir_resumen_mercado(df: pd.DataFrame, tablas: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Comprime las metricas clave en un dict JSON-friendly para el LLM."""
    def _a_registros(nombre: str, n: int | None = None):
        t = tablas.get(nombre)
        if t is None or t.empty:
            return []
        t = t.head(n) if n else t
        return t.round(2).to_dict(orient="records")

    precio = pd.to_numeric(df["precio"], errors="coerce")
    resumen = {
        "total_inmuebles": int(len(df)),
        "total_barrios": int(df["barrio"].nunique()),
        "precio": {
            "media": round(float(precio.mean()), 0),
            "mediana": round(float(precio.median()), 0),
            "min": round(float(precio.min()), 0),
            "max": round(float(precio.max()), 0),
            "desv_std": round(float(precio.std()), 0),
        },
        "area_mediana": round(float(pd.to_numeric(df["area"], errors="coerce").median()), 1),
        "top_barrios_oferta": _a_registros("distribucion_geografica", 8),
        "tendencia_central_top": _a_registros("tendencia_central", 8),
        "ranking_valor_m2_top": _a_registros("ranking_valor_m2", 8),
        "correlaciones_precio": (
            tablas["matriz_correlacion"].set_index("variable")["precio"].round(3).to_dict()
            if "matriz_correlacion" in tablas else {}
        ),
        "impacto_habitaciones": _a_registros("impacto_habitaciones"),
        "impacto_banos": _a_registros("impacto_banos"),
    }
    return resumen


# ---------------------------------------------------------------------------
# 4.b Recomendador por presupuesto (orientacion segun condicion economica)
# ---------------------------------------------------------------------------
def recomendar_por_presupuesto(
    df: pd.DataFrame,
    presupuesto: float,
    tolerancia: float = 0.10,
    habitaciones_min: int | None = None,
    barrios: list | None = None,
    n: int = 12,
) -> pd.DataFrame:
    """Recomienda inmuebles segun la capacidad economica del usuario.

    Estrategia:
      1. Filtra por un rango sensato alrededor del presupuesto (canon objetivo):
         [presupuesto*0.6, presupuesto*(1+tolerancia)] para no malgastar ni
         excederse demasiado.
      2. Aplica preferencias opcionales (habitaciones minimas, barrios).
      3. Calcula un 'score de valor': que tan bueno es el valor/m2 del inmueble
         frente a la mediana de SU barrio (mientras mas barato vs su zona, mejor),
         combinado con cuanto del presupuesto aprovecha.

    Devuelve los `n` mejores con una columna 'recomendacion' explicativa.
    """
    d = df.copy()
    d["precio"] = pd.to_numeric(d["precio"], errors="coerce")
    d["area"] = pd.to_numeric(d["area"], errors="coerce")
    if "valor_m2" not in d.columns:
        d["valor_m2"] = d["precio"] / d["area"]

    piso = presupuesto * 0.6
    techo = presupuesto * (1 + tolerancia)
    d = d[d["precio"].between(piso, techo)]

    if habitaciones_min:
        d = d[pd.to_numeric(d["habitaciones"], errors="coerce") >= habitaciones_min]
    if barrios:
        d = d[d["barrio"].isin(barrios)]

    d = d.dropna(subset=["precio", "valor_m2"])
    if d.empty:
        return d

    # Valor relativo: valor/m2 del inmueble vs mediana de su barrio (<1 = ganga)
    mediana_barrio = d.groupby("barrio")["valor_m2"].transform("median")
    d["valor_relativo"] = d["valor_m2"] / mediana_barrio
    # Aprovechamiento del presupuesto (0..1, penaliza quedar muy por debajo)
    d["uso_presupuesto"] = (d["precio"] / presupuesto).clip(upper=1.0)
    # Score: prioriza buen valor relativo y buen aprovechamiento del presupuesto
    d["score"] = (1 / d["valor_relativo"]) * (0.5 + 0.5 * d["uso_presupuesto"])

    d = d.sort_values("score", ascending=False).head(n).reset_index(drop=True)

    def _texto(row):
        vs = (1 - row["valor_relativo"]) * 100
        pos = f"{abs(vs):.0f}% {'por debajo' if vs >= 0 else 'por encima'} del m² típico de {row['barrio']}"
        return (f"{row['barrio']}: ${row['precio']:,.0f}/mes · {row['area']:.0f} m² · "
                f"{int(row['habitaciones'])} hab · {pos}")

    d["recomendacion"] = d.apply(_texto, axis=1)
    return d


# ---------------------------------------------------------------------------
# 5. Persistencia (capa processed + BI)
# ---------------------------------------------------------------------------
def _exportar(df: pd.DataFrame, tablas: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """Persiste la tabla de hechos y las tablas analiticas (CSV + Parquet)."""
    config.asegurar_directorios()
    archivos: Dict[str, str] = {}

    # Tabla de hechos (con valor_m2 si existe) -> processed/
    fact = tablas.get("fact_con_valor_m2", df)
    fact_csv = config.PROCESSED_DIR / "inmuebles_procesados.csv"
    fact.to_csv(fact_csv, index=False, encoding="utf-8")
    archivos["fact_csv"] = str(fact_csv)

    try:  # Parquet es opcional (requiere pyarrow); ideal para Power BI
        fact_parquet = config.PROCESSED_DIR / "inmuebles_procesados.parquet"
        fact.to_parquet(fact_parquet, index=False)
        archivos["fact_parquet"] = str(fact_parquet)
    except Exception as exc:  # noqa: BLE001
        print(f"  [info] Parquet omitido (instala pyarrow para habilitarlo): {exc}")

    # Tablas analiticas -> processed/bi/ (consumibles directo por Power BI)
    for nombre, tabla in tablas.items():
        if tabla is None or not isinstance(tabla, pd.DataFrame):
            continue
        ruta = config.BI_DIR / f"{nombre}.csv"
        tabla.to_csv(ruta, index=False, encoding="utf-8")
        archivos[nombre] = str(ruta)

    return archivos


# ---------------------------------------------------------------------------
# 6. Orquestacion principal
# ---------------------------------------------------------------------------
def run_pipeline(fuente: Union[str, Path] = "datalake", exportar: bool = True,
                 control_calidad: bool = True) -> ResultadoPipeline:
    """Ejecuta el flujo completo y devuelve un ResultadoPipeline."""
    print(f"== Pipeline inmobiliario | fuente={fuente} ==")

    df_crudo = _cargar_dataframe(fuente)
    print(f"1) Extraccion: {len(df_crudo)} registros crudos.")

    df = _preparar(df_crudo, control_calidad=control_calidad)
    print(f"2) Limpieza: {len(df)} inmuebles unicos, {df['barrio'].nunique()} barrios.")

    tablas = calcular_estadisticas(df)
    print(f"3) Analitica: {len(tablas)} tablas calculadas.")

    resumen = construir_resumen_mercado(df, tablas)

    archivos: Dict[str, str] = {}
    if exportar:
        archivos = _exportar(df, tablas)
        print(f"4) Exportacion: {len(archivos)} archivos en {config.PROCESSED_DIR}.")

    return ResultadoPipeline(
        df=df, tablas=tablas, resumen_mercado=resumen,
        fuente=str(fuente), archivos=archivos,
    )
