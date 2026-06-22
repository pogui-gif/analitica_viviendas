# 🏙️ Inteligencia Inmobiliaria — Arriendos en Bogotá

Pipeline de datos **end-to-end** que extrae ofertas de arriendo del portal
**Metrocuadrado**, las limpia y analiza, y las expone a través de un **dashboard
interactivo** y una **capa BI** (Power BI), con un **agente de IA** que genera
proyecciones y sugerencias estratégicas de inversión.

> Proyecto educativo de Data Engineering: ETL → Analítica → BI → IA, orquestado
> en Python y desplegable en una VM (Vagrant/Ubuntu).

---

## 🗺️ Arquitectura

```
            ┌──────────── DATALAKE (Google Drive) ────────────┐
            │   viviendas_drive/datos/raw/01/{fecha}/*.html    │
            └──────────────────────────────────────────────────┘
                        │  fetch.py (Playwright: scroll + Shadow DOM)
                        ▼
   extract ─► clean ─► dedup ─► control_calidad ─► stats (analítica)
                        │
        ┌───────────────┼─────────────────────────┐
        ▼               ▼                         ▼
   data/processed/  data/processed/bi/        ai_agent (LLM)
   (tabla hechos)   (tablas analíticas)       reporte de inversión .md
        │               │                         │
        ▼               ▼                         ▼
    Streamlit  ◄──── Power BI ◄────── proyecciones / sugerencias
```

Detalle completo en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## 📂 Estructura del repositorio

```
.
├── src/modulo_analitics/      # Paquete Python (lógica del pipeline)
│   ├── extract.py             # HTML → DataFrame
│   ├── clean.py               # Normalización, IDs, tipos, NaN
│   ├── stats.py               # Analítica descriptiva y de mercado
│   ├── config.py              # Rutas, datalake, settings LLM
│   ├── fetch.py               # Scraping Playwright + acceso al datalake
│   ├── drive.py               # Sincronización con Google Drive (gdown)
│   ├── pipeline.py            # Orquestador + control de calidad
│   └── ai_agent.py            # Agente IA multi-proveedor (LM Studio/Claude)
├── tests/                     # Pruebas unitarias (pytest)
├── dashboard/app.py           # Dashboard Streamlit (gráficos + chatbot asesor)
├── scripts/                   # Lanzadores (run_dashboard.sh/.bat) + acceso directo
├── assets/                    # Ícono del dashboard (favicon / acceso directo)
├── data/sample/               # Dataset de muestra (corre offline)
├── docs/                      # Arquitectura, guía Power BI, notebooks, negocio
├── main.py                    # CLI de orquestación
├── pyproject.toml             # Empaquetado + deps + pytest
├── requirements.txt
└── Vagrantfile                # Entorno de VM reproducible
```

## 🚀 Inicio rápido

```bash
# 1. Instalar (modo editable) con el stack completo
pip install -e ".[all]"

# 2. Correr offline con datos de muestra (no requiere Drive ni Playwright)
python main.py --fuente sample

# 3. Procesar el datalake real (apuntando a la carpeta de Drive)
#    Linux/VM:
DATALAKE_DIR="viviendas_drive/datos/raw" python main.py --fuente datalake
#    Windows (PowerShell):
#    $env:DATALAKE_DIR="viviendas_drive\datos\raw"; py main.py --fuente datalake
```

### Dashboard (interfaz interactiva)

```bash
# Lanzador automático (instala deps, procesa datos y abre la interfaz)
./scripts/run_dashboard.sh          # Linux / VM Vagrant → http://192.168.33.10:8501
scripts\run_dashboard.bat           # Windows (doble clic) → http://localhost:8501
```

Cuatro pestañas pensadas para un usuario externo:
- **📊 Panorama** — KPIs, distribución, segmentación, valor/m² y correlaciones.
- **🔎 Buscar inmuebles** — filtros con listas desplegables (barrio, habitaciones,
  baños, parqueaderos, área), buscador por texto y **tarjetas con imágenes** + enlace.
- **🎯 Recomendador por presupuesto** — ingresa tu canon o ingreso y obtén las
  mejores opciones según tu condición económica, con orientación de la IA.
- **💬 Asesor IA** — reporte estratégico + chatbot conversacional.

## 🔌 Fuentes de datos (`--fuente`)

| Valor | Qué hace |
|---|---|
| `sample` | Dataset de muestra incluido (offline) |
| `datalake` | HTML/CSV más reciente del datalake local (`DATALAKE_DIR`) |
| `drive` | Descarga el datalake desde Google Drive con `gdown` |
| `scrape` | Scrapea Metrocuadrado en vivo (requiere Playwright) |
| ruta `.html`/`.csv` | Procesa un archivo puntual |

## 🤖 Agente de IA

Multi-proveedor (patrón Strategy), seleccionable con `LLM_PROVIDER`:

- **`lmstudio`** (default) — LLM local vía API compatible con OpenAI.
- **`gemini`** — Google Gemini, SDK `google-genai` (requiere `GEMINI_API_KEY`).
- **`anthropic`** — Claude (requiere `ANTHROPIC_API_KEY`).
- **`none`** — fallback determinista (sin red), garantiza salida siempre.

```bash
# Gemini (respuestas elaboradas)
export GEMINI_API_KEY="tu_clave"
python main.py --fuente datalake --proveedor-ia gemini
```

Tres capacidades:
1. **Reporte de inversión** a nivel mercado (`generar_reporte_mercado`).
2. **Evaluación de un inmueble** vs. el mercado (`evaluar_inmueble`).
3. **Chatbot asesor** conversacional en el dashboard (`responder_chat`), que
   responde anclado a los datos y filtros que el usuario está viendo.

## 📊 Power BI

El pipeline exporta tablas BI-ready a `data/processed/bi/`. Guía de conexión y
medidas DAX en [docs/PowerBI_Guia.md](docs/PowerBI_Guia.md).

## 🧪 Pruebas

```bash
pytest          # usa la config de pyproject.toml (pythonpath=src)
```

## 🖥️ Despliegue en VM (Vagrant)

```bash
vagrant up && vagrant ssh
# dentro de la VM, el proyecto está en /vagrant
cd /vagrant && pip install -e ".[dashboard]"
./scripts/run_dashboard.sh
```

## 🛠️ Stack

Python · pandas · BeautifulSoup · Playwright · Streamlit · Plotly · gdown ·
LM Studio / Anthropic · Vagrant.

## ⚠️ Notas

- Los datos crudos (`viviendas_drive/`, `data/raw`, `data/processed`) **no se
  versionan** (ver `.gitignore`); viven en Google Drive.
- Uso educativo. Respeta los términos de servicio y políticas de datos de
  Metrocuadrado al scrapear.
