"""
Configuracion central del pipeline de inteligencia inmobiliaria.

Toda ruta o parametro que cambie entre entornos (local, VM Vagrant, datalake en
Google Drive) se resuelve aqui, leyendo variables de entorno con valores por
defecto sensatos. Asi el resto de los modulos no conocen rutas absolutas.

Variables de entorno relevantes
--------------------------------
DATALAKE_DIR   Carpeta raiz del datalake de HTML crudo. Apuntala a tu carpeta
               sincronizada de Google Drive para Escritorio, ej:
               set DATALAKE_DIR=G:\\Mi unidad\\vivendas_bogota\\data\\raw
PROCESSED_DIR  Carpeta de salida para datos procesados / BI / reportes.
SCRAPE_URL     URL de Metrocuadrado a scrapear.

LLM_PROVIDER   "lmstudio" (default) | "anthropic" | "none"
LMSTUDIO_BASE_URL   Endpoint OpenAI-compatible de LM Studio.
LMSTUDIO_MODEL      Nombre del modelo cargado en LM Studio.
ANTHROPIC_API_KEY   Clave para usar Claude.
ANTHROPIC_MODEL     ID del modelo Claude.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Raices del proyecto ---------------------------------------------------
# config.py vive en src/modulo_analitics/ ; subimos 2 niveles -> raiz del repo
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parents[1]          # raiz del repo (contiene src/, data/...)
DEFAULT_DATA_DIR = PROJECT_DIR / "data"


def _env_path(var: str, default: Path) -> Path:
    valor = os.environ.get(var)
    return Path(valor).expanduser() if valor else default


# --- Rutas del datalake / capas de datos -----------------------------------
# data/raw/metrocuadrado/{fecha}/pagina_1_rendered.html   (estructura del notebook v2)
DATALAKE_DIR = _env_path("DATALAKE_DIR", DEFAULT_DATA_DIR / "raw")
PROCESSED_DIR = _env_path("PROCESSED_DIR", DEFAULT_DATA_DIR / "processed")
SAMPLE_DIR = DEFAULT_DATA_DIR / "sample"

# Subcarpetas de salida
BI_DIR = PROCESSED_DIR / "bi"            # exports tabulares para Power BI
REPORTS_DIR = PROCESSED_DIR / "reports"  # reportes generados por el agente IA

PORTAL = "metrocuadrado"

# --- Google Drive (datalake remoto) ----------------------------------------
# Link compartido de la CARPETA del datalake o de un ARCHIVO concreto, o su id.
# Acepta cualquiera de las formas que entiende gdown:
#   https://drive.google.com/drive/folders/<ID>      (carpeta)
#   https://drive.google.com/file/d/<ID>/view         (archivo)
#   <ID>                                              (id pelado)
DRIVE_URL = os.environ.get("DRIVE_URL", "")
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID", "")
# "folder" descarga una carpeta recursiva; "file" descarga un unico archivo.
DRIVE_TIPO = os.environ.get("DRIVE_TIPO", "folder").lower()

# --- Scraping ---------------------------------------------------------------
SCRAPE_URL = os.environ.get(
    "SCRAPE_URL",
    "https://www.metrocuadrado.com/apartamento-apartaestudio/arriendo/bogota/",
)
SCRAPE_MAX_SCROLLS = int(os.environ.get("SCRAPE_MAX_SCROLLS", "30"))

# --- Esquema de columnas (contrato del pipeline) ----------------------------
# Orden y nombres que produce clean.limpiar_datos(). Lo centralizamos para que
# pipeline, dashboard y agente compartan una sola fuente de verdad.
COLUMNAS_LIMPIAS = [
    "href", "url_img", "alt_img", "barrio", "servicio", "precio_str",
    "precio", "area", "habitaciones", "banos", "parqueaderos", "id", "link",
]
COLUMNAS_NUMERICAS = ["precio", "area", "habitaciones", "banos", "parqueaderos"]

# --- Control de calidad / saneamiento de outliers ---------------------------
# Los listados "En Venta y Arriendo" muestran el PRECIO DE VENTA (miles de
# millones), no el canon; los excluimos del analisis de arriendo. Las cotas de
# dominio descartan errores de digitacion y cuotas de administracion.
FILTRAR_VENTA = os.environ.get("FILTRAR_VENTA", "1") == "1"
FILTRAR_OUTLIERS = os.environ.get("FILTRAR_OUTLIERS", "1") == "1"
PRECIO_MIN = int(os.environ.get("PRECIO_MIN", "400000"))        # piso arriendo realista
PRECIO_MAX = int(os.environ.get("PRECIO_MAX", "100000000"))     # techo ultra-lujo (100M)

# --- Configuracion del agente de IA -----------------------------------------
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "lmstudio").lower()

# LM Studio expone una API compatible con OpenAI en localhost:1234 por defecto.
LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "local-model")
LMSTUDIO_API_KEY = os.environ.get("LMSTUDIO_API_KEY", "lm-studio")  # LM Studio ignora el valor

# Anthropic / Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Google Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1500"))


def asegurar_directorios() -> None:
    """Crea las carpetas de salida si no existen (idempotente)."""
    for carpeta in (PROCESSED_DIR, BI_DIR, REPORTS_DIR, DATALAKE_DIR):
        carpeta.mkdir(parents=True, exist_ok=True)
