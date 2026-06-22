# Arquitectura — Plataforma de Inteligencia Inmobiliaria (Bogotá)

## 1. Visión

Pipeline de datos end-to-end que extrae ofertas de arriendo de **Metrocuadrado**,
las limpia, calcula analítica descriptiva y de mercado, y las expone a través de
**dos capas de consumo**: un **dashboard interactivo (Streamlit)** y una **capa
BI lista para Power BI**, con un **agente de IA** que genera proyecciones y
sugerencias estratégicas de inversión.

## 2. Diagrama de flujo

```
            ┌────────────────────── DATALAKE (Google Drive) ──────────────────────┐
            │   data/raw/metrocuadrado/{fecha}/pagina_1_rendered.html              │
            └─────────────────────────────────────────────────────────────────────┘
                        ▲ (fetch.py · Playwright: scroll + Shadow DOM)
                        │
   [scrape en vivo] ────┘                         [sample / .csv / .html]
                        │                                   │
                        ▼                                   ▼
   ┌──────────────────────────────  pipeline.run_pipeline()  ──────────────────────────────────────┐
   │  extract (multi-página)  →  clean  →  dedup  →  control_calidad  →  stats.* (analítica)        │
   └───────────────────────────────────────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼─────────────────────────────┐
        ▼               ▼                             ▼
  data/processed/   data/processed/bi/          ai_agent (LLM)
  inmuebles_*.csv   *.csv (tablas analíticas)    resumen_mercado → reporte .md
  inmuebles_*.parquet      │                            │
        │                  │                            │
        ▼                  ▼                            ▼
   Streamlit  ◄────────  Power BI  ◄───────  data/processed/reports/*.md
   (dashboard)          (BI ejecutivo)        (proyecciones / sugerencias)
```

## 3. Componentes (módulos)

| Módulo | Responsabilidad | Estado |
|---|---|---|
| `extract.py` | HTML → DataFrame (parsing BeautifulSoup) | existente |
| `clean.py` | Normalización, IDs, tipos, NaN | existente |
| `stats.py` | Analítica descriptiva y de mercado | existente |
| `config.py` | Rutas, `DATALAKE_DIR`, settings LLM | **nuevo** |
| `fetch.py` | Scraping Playwright + acceso al datalake | **nuevo** |
| `pipeline.py` | Orquestación E→C→A→exports + resumen IA | **nuevo** |
| `ai_agent.py` | Agente evaluador multi-proveedor | **nuevo** |
| `main.py` | CLI de orquestación | **nuevo** |
| `dashboard/app.py` | Dashboard Streamlit | **nuevo** |

## 4. Contrato de datos

La **tabla de hechos** (`inmuebles_procesados.csv/.parquet`) tiene el esquema
definido en `config.COLUMNAS_LIMPIAS`:

```
href, url_img, alt_img, barrio, servicio, precio_str, precio,
area, habitaciones, banos, parqueaderos, id, link [, valor_m2]
```

Las **tablas analíticas** (`data/processed/bi/*.csv`) son las salidas de `stats.py`
(distribución geográfica, tendencia central + segmento, ranking valor/m², matriz
de correlación, impacto de características). Estas son las que consume Power BI.

## 4.b Control de calidad (saneamiento de outliers)

El datalake real mezcla ruido que distorsiona la analítica de arriendo. El paso
`aplicar_control_calidad()` lo corrige de forma **transparente y configurable**
(reporta cada exclusión por consola):

1. **Listados "En Venta y Arriendo"** → muestran el *precio de venta* (miles de
   millones), no el canon. Se excluyen (`FILTRAR_VENTA`).
2. **Cotas de dominio** `[PRECIO_MIN, PRECIO_MAX]` → descartan errores de
   digitación y cuotas de administración (`FILTRAR_OUTLIERS`).

> Impacto medido sobre los datos reales (2026-04-28, 448 inmuebles): excluir 4
> registros corruptos elevó la correlación **precio~área de 0.13 → 0.84**. Sin
> este paso, el análisis y el agente IA producen conclusiones erróneas.

Se desactiva con `--sin-control-calidad`. Estructura real del datalake soportada:
`datos/raw/01/{fecha}/pagina_{1..8}_rendered.html` (multi-página, concatenada).

## 5. Decisiones de diseño

- **Fuente desacoplada** (`datalake` / `scrape` / `sample` / ruta): el pipeline no
  depende de cómo llegan los datos. `DATALAKE_DIR` apunta a la carpeta sincronizada
  de Google Drive para Escritorio o a una copia local.
- **Agente IA con patrón Strategy** (`LLMProvider`): LM Studio (local), Claude
  (Anthropic) y un *fallback determinista* que garantiza salida sin red. Se elige
  con `LLM_PROVIDER`.
- **Resiliencia**: cada cálculo de `stats` está aislado; un fallo no tumba el flujo.
  Parquet es opcional (degradación elegante a solo CSV).
- **Dos capas de BI**: Streamlit (programático, corre en la VM Vagrant) + Power BI
  (ejecutivo, consume los CSV/Parquet). Ambas leen los mismos artefactos.

## 6. Ejecución

```bash
# ETL + analítica + reporte IA, offline con muestra
python main.py --fuente sample

# Producción desde una carpeta de Drive YA sincronizada (Drive para Escritorio)
set DATALAKE_DIR=G:\Mi unidad\vivendas_bogota\data\raw
python main.py --fuente datalake --proveedor-ia lmstudio

# Descarga AUTOMÁTICA desde un enlace de Drive (requiere: pip install gdown)
python main.py --fuente drive --drive-url "https://drive.google.com/drive/folders/<ID>"
# ...o un archivo único (HTML/CSV):
python main.py --fuente drive --drive-tipo file --drive-url "https://drive.google.com/file/d/<ID>/view"

# Dashboard
streamlit run dashboard/app.py
```

### Sincronización con Google Drive (`drive.py`)

`--fuente drive` descarga el datalake remoto con `gdown` y luego procesa:

1. Comparte la carpeta/archivo en Drive como **"Cualquier persona con el enlace" (lector)**.
2. `pip install gdown`.
3. Pasa el enlace por `--drive-url` o la variable `DRIVE_URL`.

- **Carpeta** (`DRIVE_TIPO=folder`, default): replica `data/raw/metrocuadrado/{fecha}/*.html`
  en `DATALAKE_DIR` y procesa el HTML más reciente.
- **Archivo** (`DRIVE_TIPO=file`): descarga un único `.html` o `.csv`. Si es el
  `salida.csv` del notebook (con índice y sin encabezados nombrados), el pipeline
  lo normaliza automáticamente.

## 7. Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `DATALAKE_DIR` | `data/raw` | Raíz del datalake (apuntar a Drive) |
| `DRIVE_URL` | — | Link/id de la carpeta o archivo de Drive |
| `DRIVE_TIPO` | `folder` | `folder` (recursivo) o `file` (único) |
| `FILTRAR_VENTA` | `1` | Excluir listados de venta |
| `FILTRAR_OUTLIERS` | `1` | Aplicar cotas de precio |
| `PRECIO_MIN` / `PRECIO_MAX` | `400000` / `100000000` | Rango válido de canon |
| `PROCESSED_DIR` | `data/processed` | Salidas procesadas |
| `SCRAPE_URL` | URL arriendos Bogotá | Objetivo del scraper |
| `LLM_PROVIDER` | `lmstudio` | `lmstudio` / `gemini` / `anthropic` / `none` |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | Endpoint LM Studio |
| `LMSTUDIO_MODEL` | `local-model` | Modelo cargado en LM Studio |
| `ANTHROPIC_API_KEY` | — | Clave Claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Modelo Claude |
| `GEMINI_API_KEY` | — | Clave Google Gemini (o `GOOGLE_API_KEY`) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modelo Gemini |
