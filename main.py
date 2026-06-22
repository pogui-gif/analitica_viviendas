"""
Punto de entrada (CLI) del pipeline de inteligencia inmobiliaria.

Orquesta el flujo completo: obtencion -> limpieza -> analitica -> exports BI ->
agente de IA. Disenado para correr identico en local, en la VM Vagrant o en CI.

Ejemplos
--------
    # Flujo completo desde el datalake (Drive) + reporte IA
    python main.py --fuente datalake

    # Correr offline con datos de muestra (no requiere Drive ni Playwright)
    python main.py --fuente sample

    # Scrapear en vivo (requiere playwright) y luego procesar
    python main.py --fuente scrape

    # Procesar y forzar el proveedor de IA
    python main.py --fuente sample --proveedor-ia anthropic
    python main.py --fuente sample --sin-ia        # solo ETL + analitica
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite ejecutar `python main.py` sin instalar el paquete: agrega src/ al path.
SRC = Path(__file__).resolve().parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modulo_analitics import ai_agent, pipeline  # noqa: E402


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Pipeline de inteligencia inmobiliaria - Bogota")
    p.add_argument(
        "--fuente", default="datalake",
        help="datalake | drive | scrape | sample | ruta a .html/.csv (default: datalake)",
    )
    p.add_argument("--drive-url", default=None, help="Link/id de Drive (fuente=drive).")
    p.add_argument("--drive-tipo", default=None, choices=["folder", "file"],
                   help="Descargar carpeta o archivo de Drive (default: config).")
    p.add_argument("--sin-ia", action="store_true", help="No ejecutar el agente de IA.")
    p.add_argument("--sin-export", action="store_true", help="No persistir archivos en disco.")
    p.add_argument("--sin-control-calidad", action="store_true",
                   help="No filtrar listados de venta ni outliers de precio.")
    p.add_argument(
        "--proveedor-ia", default=None,
        help="Forzar proveedor del agente: lmstudio | anthropic | none.",
    )
    p.add_argument(
        "--evaluar-inmuebles", type=int, default=0, metavar="N",
        help="Ademas del reporte, evaluar los N inmuebles mas economicos por m2.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    # Overrides de Drive en tiempo de ejecucion (sin tocar variables de entorno)
    from modulo_analitics import config  # noqa: E402
    if args.drive_url:
        config.DRIVE_URL = args.drive_url
    if args.drive_tipo:
        config.DRIVE_TIPO = args.drive_tipo

    # 1-4. ETL + analitica + exports
    resultado = pipeline.run_pipeline(
        fuente=args.fuente, exportar=not args.sin_export,
        control_calidad=not args.sin_control_calidad,
    )

    # 5. Soporte de IA
    if not args.sin_ia:
        print("5) Agente de IA: generando reporte de inversion...")
        ai_agent.generar_y_guardar_reporte(
            resultado.resumen_mercado, proveedor=args.proveedor_ia,
        )
        if args.evaluar_inmuebles > 0:
            evaluacion = ai_agent.evaluar_top_inmuebles(
                resultado.df, resultado.resumen_mercado,
                n=args.evaluar_inmuebles, proveedor=args.proveedor_ia,
            )
            print("\n=== Evaluacion de inmuebles destacados ===\n")
            print(evaluacion)

    print("\nListo. Revisa data/processed/ para los entregables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
