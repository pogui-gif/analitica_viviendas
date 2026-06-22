"""
Capa de obtencion de datos (Extract - fase 1 del ETL).

Encapsula la logica de scraping dinamico que originalmente vivia en el notebook
de Colab (scroll infinito + expansion de Shadow DOM con Playwright) y la integra
a la estructura de datalake:

    {DATALAKE_DIR}/metrocuadrado/{fecha}/pagina_1_rendered.html

Playwright es una dependencia OPCIONAL: si no esta instalada, este modulo no
rompe el import del paquete; solo falla si intentas scrapear en vivo. Para el
analisis basta con tener el HTML crudo en el datalake (descargado desde Drive).

Uso:
    python -m modulo_analitics.fetch          # scrapea y guarda en el datalake
    from modulo_analitics import fetch
    ruta = fetch.localizar_html_mas_reciente() # ruta al raw mas nuevo
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import config

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _base_busqueda(datalake_dir: Optional[Path] = None) -> Path:
    """Raiz de busqueda: usa {datalake}/{portal} si existe, si no el datalake."""
    base = Path(datalake_dir or config.DATALAKE_DIR)
    con_portal = base / config.PORTAL
    return con_portal if con_portal.exists() else base


def _particion_reciente(base: Path, patron: str) -> List[Path]:
    """Devuelve TODOS los archivos `patron` de la particion (carpeta) mas nueva.

    Soporta estructuras anidadas y multi-pagina, p.ej.:
        datos/raw/01/2026-04-28/pagina_{1..8}_rendered.html
    Elige la carpeta cuya ruta contenga la fecha (YYYY-MM-DD) mas alta y devuelve
    todos los archivos coincidentes dentro de ella (todas las paginas).
    """
    archivos = list(base.rglob(patron))
    if not archivos:
        return []

    def clave_fecha(p: Path):
        fechas = [seg for seg in p.parts if _DATE_RE.fullmatch(seg)]
        return (fechas[-1] if fechas else "", str(p.parent))

    carpeta = max(archivos, key=clave_fecha).parent
    return sorted(carpeta.glob(patron))


# --- 1. Localizacion del HTML/CSV crudo en el datalake ---------------------

def localizar_htmls_recientes(datalake_dir: Optional[Path] = None) -> List[Path]:
    """Todas las paginas .html de la particion de fecha mas reciente."""
    return _particion_reciente(_base_busqueda(datalake_dir), "*.html")


def localizar_csvs_recientes(datalake_dir: Optional[Path] = None) -> List[Path]:
    """Todas las paginas .csv de la particion de fecha mas reciente."""
    return _particion_reciente(_base_busqueda(datalake_dir), "*.csv")


def localizar_html_mas_reciente(datalake_dir: Optional[Path] = None) -> Optional[Path]:
    """Ultima pagina .html de la particion reciente (compatibilidad)."""
    htmls = localizar_htmls_recientes(datalake_dir)
    return htmls[-1] if htmls else None


def leer_html(ruta: Path) -> str:
    """Lee el contenido HTML de un archivo del datalake."""
    return Path(ruta).read_text(encoding="utf-8")


# --- 2. Scraping en vivo con Playwright (opcional) -------------------------

async def _scroll_page(page, max_scrolls: int = config.SCRAPE_MAX_SCROLLS) -> None:
    """Fuerza la carga de todas las tarjetas haciendo scroll (scroll infinito)."""
    previo = 0
    sin_cambio = 0
    for i in range(max_scrolls):
        cards = await page.query_selector_all(".property-card__container")
        actual = len(cards)
        print(f"Scroll {i}: {actual}")

        sin_cambio = sin_cambio + 1 if actual == previo else 0
        if sin_cambio >= 3:
            print("No cargan mas resultados")
            break

        previo = actual
        await page.mouse.wheel(0, 2000)
        try:
            await page.wait_for_function(
                f"document.querySelectorAll('.property-card__container').length > {previo}",
                timeout=5000,
            )
        except Exception:
            pass


async def _get_rendered_html(page) -> str:
    """Renderiza el DOM expandiendo el Shadow DOM (web components de Metrocuadrado)."""
    return await page.evaluate(
        """
        () => {
            function expand(element) {
                if (element.shadowRoot) {
                    element.innerHTML = element.shadowRoot.innerHTML;
                }
                element.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) { el.innerHTML = el.shadowRoot.innerHTML; }
                });
            }
            expand(document.documentElement);
            return document.documentElement.outerHTML;
        }
        """
    )


async def _scrape_async(url: str, destino: Path) -> Path:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright no esta instalado. Instala con:\n"
            "    pip install playwright && playwright install chromium\n"
            "O trabaja con HTML crudo ya descargado en el datalake."
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector(".property-card__container")
        await _scroll_page(page)
        html = await _get_rendered_html(page)
        await browser.close()

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"\nHTML renderizado guardado en:\n{destino}")
    return destino


def scrapear(url: str = config.SCRAPE_URL, fecha: Optional[str] = None) -> Path:
    """Scrapea Metrocuadrado y guarda el HTML renderizado en el datalake.

    Devuelve la ruta del archivo guardado. `fecha` se inyecta para poder
    parametrizar la particion (por defecto la fecha de hoy).
    """
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    destino = Path(config.DATALAKE_DIR) / config.PORTAL / fecha / "pagina_1_rendered.html"
    return asyncio.run(_scrape_async(url, destino))


if __name__ == "__main__":  # pragma: no cover
    scrapear()
