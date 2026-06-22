@echo off
REM ============================================================
REM  Lanzador del dashboard inmobiliario (Windows - doble clic)
REM  Auto-configura dependencias y datos, y abre la interfaz.
REM ============================================================
setlocal enabledelayedexpansion

REM Ir a la raiz del repo, sin importar desde donde se ejecute
cd /d "%~dp0\.."

REM Datalake real (relativo al proyecto). Ajustable creando la variable antes.
if not defined DATALAKE_DIR set "DATALAKE_DIR=%CD%\viviendas_drive\datos\raw"
if not defined PORT set "PORT=8501"

echo === Verificando dependencias ===
py -c "import streamlit, plotly, pandas, bs4" 2>NUL
if errorlevel 1 (
    echo Instalando dependencias del dashboard...
    py -m pip install --quiet --upgrade pip
    py -m pip install --quiet pandas numpy beautifulsoup4 streamlit plotly
)

REM Generar datos procesados si no existen
if not exist "data\processed\inmuebles_procesados.csv" (
    echo === Procesando datos ===
    if exist "%DATALAKE_DIR%" (
        py main.py --fuente datalake --sin-ia
    ) else (
        echo   Datalake no encontrado; usando datos de muestra.
        py main.py --fuente sample --sin-ia
    )
)

echo.
echo ==================================================================
echo   Abriendo dashboard en http://localhost:%PORT%
echo   Detener: cierra esta ventana o Ctrl+C
echo ==================================================================
echo.

REM Abrir el navegador y lanzar Streamlit (se mantiene corriendo en esta ventana)
start "" "http://localhost:%PORT%"
py -m streamlit run dashboard/app.py --server.port=%PORT%

endlocal
