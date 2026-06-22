"""
Dashboard interactivo de inteligencia inmobiliaria (Streamlit).

Pensado para un usuario externo: explora el mercado, busca inmuebles con filtros
e imagenes, recibe recomendaciones segun su presupuesto y conversa con un asesor
de IA. Consume los DataFrames procesados por el pipeline (data/processed/).

Ejecutar:
    pip install streamlit plotly
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# --- Hacer importable el paquete (src/) ------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modulo_analitics import ai_agent, config, pipeline  # noqa: E402

# Favicon: usa el icono del proyecto si existe; si no, un emoji.
_ICONO = RAIZ / "assets" / "dashboard_icon.ico"
_PAGE_ICON = str(_ICONO) if _ICONO.exists() else "🏙️"
st.set_page_config(page_title="Inteligencia Inmobiliaria · Bogotá",
                   page_icon=_PAGE_ICON, layout="wide")


# ===========================================================================
# Carga de datos
# ===========================================================================
@st.cache_data(show_spinner=False)
def cargar_fact() -> pd.DataFrame | None:
    ruta = config.PROCESSED_DIR / "inmuebles_procesados.csv"
    if not ruta.exists():
        return None
    df = pd.read_csv(ruta)
    if "valor_m2" not in df.columns:
        df["valor_m2"] = df["precio"] / df["area"]
    # Tipo derivado (Apartamento / Apartaestudio) a partir del titulo/servicio
    serv = df.get("servicio", pd.Series([""] * len(df))).astype(str).str.lower()
    df["tipo"] = serv.apply(lambda s: "Apartaestudio" if "apartaestudio" in s else "Apartamento")
    return df


def generar_datos_demo() -> None:
    with st.spinner("Procesando dataset de muestra..."):
        pipeline.run_pipeline(fuente="sample", exportar=True)
    st.cache_data.clear()


# --- Utilidades de formato / render ----------------------------------------
def _i(v) -> str:
    """Entero seguro para mostrar (maneja NaN)."""
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return "–"


def _money(v) -> str:
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "–"


def render_tarjetas(data: pd.DataFrame, columnas: int = 3) -> None:
    """Renderiza inmuebles como tarjetas con imagen, datos clave y enlace."""
    if data.empty:
        st.info("No hay inmuebles que coincidan con los criterios.")
        return
    filas = data.reset_index(drop=True)
    for inicio in range(0, len(filas), columnas):
        cols = st.columns(columnas)
        for j, col in enumerate(cols):
            k = inicio + j
            if k >= len(filas):
                break
            r = filas.iloc[k]
            with col:
                with st.container(border=True):
                    img = r.get("url_img")
                    if isinstance(img, str) and img.startswith("http"):
                        st.image(img, width="stretch")
                    st.markdown(f"#### {_money(r['precio'])} /mes")
                    st.markdown(f"**{r.get('barrio', '—')}**  ·  _{r.get('tipo', '')}_")
                    st.caption(
                        f"📐 {_i(r['area'])} m²  ·  🛏️ {_i(r['habitaciones'])} hab  ·  "
                        f"🚿 {_i(r['banos'])} baños  ·  🚗 {_i(r['parqueaderos'])} parq."
                    )
                    st.caption(f"💲 Valor/m²: {_money(r.get('valor_m2'))}")
                    if isinstance(r.get("recomendacion"), str):
                        st.success("✅ " + r["recomendacion"])
                    enlace = r.get("link")
                    if isinstance(enlace, str) and enlace.startswith("http"):
                        st.link_button("Ver en Metrocuadrado ↗", enlace, width="stretch")


def contexto_mercado(df: pd.DataFrame) -> dict:
    """Construye el resumen de mercado para el agente IA a partir de un subset."""
    return pipeline.construir_resumen_mercado(df, pipeline.calcular_estadisticas(df))


# ===========================================================================
# Encabezado y carga
# ===========================================================================
st.title("🏙️ Inteligencia Inmobiliaria — Arriendos en Bogotá")
st.caption("Explora el mercado, encuentra tu inmueble ideal y recibe orientación personalizada · Fuente: Metrocuadrado")

df = cargar_fact()
if df is None:
    st.warning("No se encontraron datos procesados en `data/processed/`.")
    if st.button("⚙️ Generar datos de muestra ahora"):
        generar_datos_demo()
        st.rerun()
    st.stop()

# ===========================================================================
# Barra lateral: filtros globales + proveedor IA
# ===========================================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    proveedor = st.selectbox(
        "Asesor de IA (proveedor)",
        ["fallback", "gemini", "lmstudio", "anthropic"],
        index=0,
        help="fallback funciona sin conexión. Gemini/LM Studio/Claude requieren clave o servidor.",
    )
    st.divider()
    st.header("🔍 Filtros globales")
    barrios = sorted(df["barrio"].dropna().unique())
    sel_barrios = st.multiselect("Barrio", barrios, default=[],
                                 placeholder="Todos los barrios")
    tipos = sorted(df["tipo"].dropna().unique())
    sel_tipos = st.multiselect("Tipo de inmueble", tipos, default=tipos)
    pmin, pmax = int(df["precio"].min()), int(df["precio"].max())
    rango = st.slider("Canon mensual (COP)", pmin, pmax, (pmin, pmax), step=100_000)

# Aplicar filtros globales
mask = df["precio"].between(*rango) & df["tipo"].isin(sel_tipos)
if sel_barrios:
    mask &= df["barrio"].isin(sel_barrios)
dff = df[mask].copy()

st.caption(f"**{len(dff)}** inmuebles seleccionados de {len(df)} · "
           f"{dff['barrio'].nunique()} barrios")

# ===========================================================================
# Pestañas
# ===========================================================================
tab_pan, tab_buscar, tab_recom, tab_ia = st.tabs(
    ["📊 Panorama", "🔎 Buscar inmuebles", "🎯 Recomendador por presupuesto", "💬 Asesor IA"]
)

# ---------------------------------------------------------------------------
# TAB 1: Panorama
# ---------------------------------------------------------------------------
with tab_pan:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Inmuebles", f"{len(dff):,}")
    c2.metric("Barrios", dff["barrio"].nunique())
    c3.metric("Canon mediano", _money(dff["precio"].median()))
    c4.metric("Valor m² mediano", _money(dff["valor_m2"].median()))
    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Distribución geográfica de la oferta")
        conteo = dff["barrio"].value_counts().head(15).reset_index()
        conteo.columns = ["barrio", "ofertas"]
        fig = px.bar(conteo, x="ofertas", y="barrio", orientation="h",
                     color="ofertas", color_continuous_scale="Blues")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=460)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        st.subheader("Segmentación de precios por barrio (top 15)")
        resumen = (dff.groupby("barrio")["precio"].median()
                   .sort_values(ascending=False).head(15)
                   .sort_values().reset_index())
        try:
            resumen["Segmento"] = pd.qcut(resumen["precio"], q=3,
                                          labels=["Económico", "Medio", "Premium"])
        except ValueError:
            resumen["Segmento"] = "N/D"
        fig = px.bar(resumen, x="precio", y="barrio", orientation="h", color="Segmento",
                     color_discrete_map={"Económico": "#74c476", "Medio": "#fd8d3c", "Premium": "#de2d26"})
        fig.update_layout(height=460)
        st.plotly_chart(fig, width="stretch")

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Valorización del metro cuadrado (top 15)")
        ranking = (dff.groupby("barrio")["valor_m2"].median()
                   .sort_values(ascending=False).head(15).sort_values().reset_index())
        fig = px.bar(ranking, x="valor_m2", y="barrio", orientation="h",
                     color="valor_m2", color_continuous_scale="Magma")
        fig.update_layout(height=460)
        st.plotly_chart(fig, width="stretch")
    with col_d:
        st.subheader("Determinantes del precio (correlación)")
        cols_num = [c for c in config.COLUMNAS_NUMERICAS if c in dff.columns]
        fig = px.imshow(dff[cols_num].corr(), text_auto=".2f", aspect="auto",
                        color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        fig.update_layout(height=460)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Relación precio · área · habitaciones")
    fig = px.scatter(dff, x="area", y="precio", color="barrio", size="habitaciones",
                     hover_data=["banos", "parqueaderos", "valor_m2"], height=480)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# TAB 2: Buscar inmuebles (filtros detallados + imágenes)
# ---------------------------------------------------------------------------
with tab_buscar:
    st.subheader("🔎 Encuentra tu inmueble")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        hab_opts = sorted(df["habitaciones"].dropna().unique().astype(int))
        sel_hab = st.multiselect("Habitaciones", hab_opts, default=[], placeholder="Cualquiera")
    with f2:
        ban_opts = sorted(df["banos"].dropna().unique().astype(int))
        sel_ban = st.multiselect("Baños", ban_opts, default=[], placeholder="Cualquiera")
    with f3:
        par_opts = sorted(df["parqueaderos"].dropna().unique().astype(int))
        sel_par = st.multiselect("Parqueaderos", par_opts, default=[], placeholder="Cualquiera")
    with f4:
        orden = st.selectbox("Ordenar por", [
            "Mejor valor/m²", "Precio: menor a mayor", "Precio: mayor a menor",
            "Área: mayor a menor",
        ])

    a1, a2 = st.columns([2, 1])
    with a1:
        amin, amax = int(df["area"].min()), int(df["area"].max())
        rango_area = st.slider("Área (m²)", amin, amax, (amin, amax))
    with a2:
        texto = st.text_input("Buscar por barrio / palabra clave", placeholder="Ej: Chapinero, Cedritos...")

    # Aplicar (parte de los filtros globales dff)
    res = dff[dff["area"].between(*rango_area)].copy()
    if sel_hab:
        res = res[pd.to_numeric(res["habitaciones"], errors="coerce").isin(sel_hab)]
    if sel_ban:
        res = res[pd.to_numeric(res["banos"], errors="coerce").isin(sel_ban)]
    if sel_par:
        res = res[pd.to_numeric(res["parqueaderos"], errors="coerce").isin(sel_par)]
    if texto:
        t = texto.strip().lower()
        res = res[res["barrio"].str.lower().str.contains(t, na=False)
                  | res.get("servicio", pd.Series("", index=res.index)).astype(str).str.lower().str.contains(t, na=False)]

    orden_map = {
        "Mejor valor/m²": ("valor_m2", True),
        "Precio: menor a mayor": ("precio", True),
        "Precio: mayor a menor": ("precio", False),
        "Área: mayor a menor": ("area", False),
    }
    col_ord, asc = orden_map[orden]
    res = res.sort_values(col_ord, ascending=asc)

    cant = st.slider("Inmuebles a mostrar", 3, min(48, max(3, len(res)) if len(res) else 3),
                     min(12, len(res)) if len(res) else 3)
    st.caption(f"**{len(res)}** resultados · mostrando {min(cant, len(res))}")
    render_tarjetas(res.head(cant), columnas=3)

# ---------------------------------------------------------------------------
# TAB 3: Recomendador por presupuesto
# ---------------------------------------------------------------------------
with tab_recom:
    st.subheader("🎯 ¿Qué inmueble conviene a tu bolsillo?")
    st.caption("Indícanos tu capacidad económica y te orientamos hacia las mejores opciones "
               "(buen valor por metro cuadrado dentro de tu rango).")

    g1, g2, g3 = st.columns(3)
    with g1:
        modo = st.radio("Calcular presupuesto desde", ["Canon mensual", "Ingreso mensual (regla 30%)"])
    with g2:
        monto = st.number_input(
            "Monto (COP)", min_value=300_000, max_value=60_000_000,
            value=2_500_000, step=100_000,
        )
    with g3:
        hab_min = st.selectbox("Habitaciones mínimas", [0, 1, 2, 3, 4],
                               format_func=lambda x: "Cualquiera" if x == 0 else f"{x}+")

    presupuesto = monto * 0.30 if modo.startswith("Ingreso") else monto
    barrios_pref = st.multiselect("Barrios de interés (opcional)", barrios, default=[])

    st.info(f"Presupuesto de canon objetivo: **{_money(presupuesto)} /mes**"
            + (f"  (30% de un ingreso de {_money(monto)})" if modo.startswith("Ingreso") else ""))

    reco = pipeline.recomendar_por_presupuesto(
        df, presupuesto=presupuesto,
        habitaciones_min=(hab_min or None),
        barrios=(barrios_pref or None),
        n=12,
    )

    if reco.empty:
        st.warning("No encontramos inmuebles en ese rango. Prueba ampliar el presupuesto "
                   "o quitar filtros de barrio/habitaciones.")
    else:
        st.success(f"Encontramos **{len(reco)}** opciones recomendadas para ti, "
                   "ordenadas por mejor relación valor/precio.")
        render_tarjetas(reco, columnas=3)

        if st.button("🤖 Pedir orientación al asesor IA", key="reco_ia"):
            with st.spinner(f"Consultando asesor ({proveedor})..."):
                top = reco.head(5)[["barrio", "precio", "area", "habitaciones", "valor_m2"]]
                pregunta = (
                    f"Mi presupuesto de arriendo es {presupuesto:,.0f} COP/mes"
                    + (f", con preferencia por {', '.join(barrios_pref)}" if barrios_pref else "")
                    + (f", minimo {hab_min} habitaciones" if hab_min else "")
                    + ". Estas son las opciones que el sistema me recomendo (JSON):\n"
                    + top.to_json(orient="records", force_ascii=False)
                    + "\n\n¿Cual me conviene mas y por que? Orientame segun mi condicion economica."
                )
                agente = ai_agent.AgenteInmobiliario(ai_agent.obtener_proveedor(proveedor))
                respuesta = agente.responder_chat(
                    [{"role": "user", "content": pregunta}], contexto_mercado(dff)
                )
            st.markdown(respuesta)

# ---------------------------------------------------------------------------
# TAB 4: Asesor IA (reporte + chatbot)
# ---------------------------------------------------------------------------
with tab_ia:
    st.subheader("🤖 Asesor virtual")
    st.caption(f"Responde según los **{len(dff)}** inmuebles filtrados. Proveedor: `{proveedor}`.")

    with st.expander("📑 Generar reporte estratégico de mercado"):
        if st.button("Generar análisis"):
            with st.spinner(f"Consultando agente ({proveedor})..."):
                agente = ai_agent.AgenteInmobiliario(ai_agent.obtener_proveedor(proveedor))
                reporte = agente.generar_reporte_mercado(contexto_mercado(dff))
            st.markdown(reporte)

    st.markdown("##### 💬 Conversa con el asesor")
    if "chat" not in st.session_state:
        st.session_state.chat = []

    cc1, cc2 = st.columns([4, 1])
    with cc2:
        if st.button("🗑️ Limpiar", width="stretch"):
            st.session_state.chat = []
            st.rerun()
    with cc1:
        st.caption("Ej: *Gano 4 millones, ¿dónde puedo vivir?* · *¿Qué influye más en el precio?* · "
                   "*¿Qué barrio tiene el m² más caro?*")

    for _msg in st.session_state.chat:
        with st.chat_message(_msg["role"]):
            st.markdown(_msg["content"])

    _pregunta = st.chat_input("Escribe tu pregunta...")
    if _pregunta:
        st.session_state.chat.append({"role": "user", "content": _pregunta})
        with st.chat_message("user"):
            st.markdown(_pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                _agente = ai_agent.AgenteInmobiliario(ai_agent.obtener_proveedor(proveedor))
                _respuesta = _agente.responder_chat(st.session_state.chat, contexto_mercado(dff))
            st.markdown(_respuesta)
        st.session_state.chat.append({"role": "assistant", "content": _respuesta})
