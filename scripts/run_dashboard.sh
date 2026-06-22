#!/usr/bin/env bash
#
# Lanzador del dashboard de inteligencia inmobiliaria (Linux / VM Vagrant).
#
# Uso:
#   ./scripts/run_dashboard.sh
#
# Hace todo automaticamente:
#   1. Crea/activa un entorno virtual (.venv).
#   2. Instala dependencias del dashboard si faltan.
#   3. Procesa el datalake si aun no hay datos (cae a 'sample' si no hay datalake).
#   4. Lanza Streamlit accesible desde el navegador del host.
#
# Variables opcionales:
#   DATALAKE_DIR  ruta del datalake (default: viviendas_drive/datos/raw)
#   PORT          puerto (default: 8501)
#
set -euo pipefail

# --- Resolver rutas relativas al repo (funciona desde cualquier cwd) -------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"            # raiz del repo
cd "$APP_DIR"

export DATALAKE_DIR="${DATALAKE_DIR:-$APP_DIR/viviendas_drive/datos/raw}"
PORT="${PORT:-8501}"

# --- Python ----------------------------------------------------------------
PY="python3"
command -v "$PY" >/dev/null 2>&1 || PY="python"

# --- Entorno virtual -------------------------------------------------------
if [ ! -d ".venv" ]; then
  echo ">> Creando entorno virtual (.venv)..."
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- Dependencias del dashboard (solo si faltan) ---------------------------
if ! python -c "import streamlit, plotly, pandas, bs4" >/dev/null 2>&1; then
  echo ">> Instalando dependencias del dashboard..."
  pip install -q --upgrade pip
  pip install -q pandas numpy beautifulsoup4 streamlit plotly
fi

# --- Asegurar datos procesados ---------------------------------------------
if [ ! -f "data/processed/inmuebles_procesados.csv" ]; then
  echo ">> No hay datos procesados; generando..."
  if [ -d "$DATALAKE_DIR" ]; then
    python main.py --fuente datalake --sin-ia
  else
    echo "   (datalake no encontrado en $DATALAKE_DIR; usando datos de muestra)"
    python main.py --fuente sample --sin-ia
  fi
fi

# --- IP de la red privada (Vagrant) ----------------------------------------
IP_PRIV="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^192\.168\.33\.' | head -1 || true)"
echo ""
echo "=================================================================="
echo "  Dashboard listo. Abre en el navegador de tu equipo (host):"
[ -n "$IP_PRIV" ] && echo "      http://$IP_PRIV:$PORT"
echo "      http://localhost:$PORT   (si lo corres en local)"
echo "  Detener: Ctrl+C"
echo "=================================================================="
echo ""

# headless=true: la VM no tiene navegador; se abre desde el host por la IP.
exec streamlit run dashboard/app.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true
