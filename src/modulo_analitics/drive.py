"""

Sincronizacion del datalake remoto en Google Drive.

Descarga el HTML crudo (o un CSV) desde una carpeta/archivo compartido de Google
Drive hacia la carpeta local DATALAKE_DIR, usando `gdown`. Asi el pipeline puede
correr con `--fuente drive` sin montar Drive manualmente.

`gdown` es una dependencia OPCIONAL: instala con `pip install gdown`.

Requisitos del lado de Drive
----------------------------
El recurso debe estar compartido como "Cualquier persona con el enlace" (lector).
Para descargas de CARPETA grandes Drive puede limitar; en ese caso comparte el
archivo (HTML/CSV) directamente y usa DRIVE_TIPO=file.

Configuracion (ver config.py):
    DRIVE_URL / DRIVE_FILE_ID   link o id del recurso
    DRIVE_TIPO                  "folder" (default) | "file"
    DATALAKE_DIR                destino local de la descarga
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from . import config


def _import_gdown():
    try:
        import gdown  # noqa: PLC0415
        return gdown
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta 'gdown'. Instala con:  pip install gdown\n"
            "Es necesario para sincronizar el datalake desde Google Drive."
        ) from exc


def _normalizar_a_id(valor: str) -> str:
    """Extrae el id de Drive desde distintas formas de URL (o lo devuelve igual)."""
    v = valor.strip()
    if "/folders/" in v:
        return v.split("/folders/")[1].split("?")[0].split("/")[0]
    if "/file/d/" in v:
        return v.split("/file/d/")[1].split("/")[0]
    if "id=" in v:
        return v.split("id=")[1].split("&")[0]
    return v  # ya es un id pelado


def descargar_archivo(url_o_id: Optional[str] = None, destino: Optional[Path] = None) -> Path:
    """Descarga un unico archivo de Drive al destino indicado."""
    gdown = _import_gdown()
    file_id = _normalizar_a_id(url_o_id or config.DRIVE_FILE_ID or config.DRIVE_URL)
    if not file_id:
        raise ValueError("Define DRIVE_URL o DRIVE_FILE_ID (o pasa url_o_id).")

    destino = Path(destino or (config.DATALAKE_DIR / config.PORTAL / "drive_download"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida = gdown.download(id=file_id, output=str(destino), quiet=False)
    if not salida:
        raise RuntimeError("gdown no pudo descargar el archivo (revisa permisos de compartido).")
    return Path(salida)


def descargar_carpeta(url_o_id: Optional[str] = None, destino: Optional[Path] = None) -> List[Path]:
    """Descarga recursivamente una carpeta de Drive dentro de DATALAKE_DIR."""
    gdown = _import_gdown()
    url = (url_o_id or config.DRIVE_URL or config.DRIVE_FILE_ID).strip()
    if not url:
        raise ValueError("Define DRIVE_URL (link de carpeta) o pasa url_o_id.")
    if not url.startswith("http"):  # gdown.download_folder prefiere URL completa
        url = f"https://drive.google.com/drive/folders/{_normalizar_a_id(url)}"

    destino = Path(destino or config.DATALAKE_DIR)
    destino.mkdir(parents=True, exist_ok=True)
    try:
        rutas = gdown.download_folder(url=url, output=str(destino), quiet=False, use_cookies=False)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "No se pudo descargar la carpeta de Drive.\n"
            "Causa probable: no es publica. En Drive abre la carpeta -> Compartir -> "
            "'Acceso general' -> 'Cualquier persona con el enlace' -> rol 'Lector'.\n"
            "Alternativa sin permisos: usa Google Drive para Escritorio y apunta "
            "DATALAKE_DIR a la carpeta sincronizada (--fuente datalake).\n"
            f"Detalle gdown: {exc}"
        ) from exc
    return [Path(r) for r in (rutas or [])]


def sincronizar_datalake(url: Optional[str] = None, tipo: Optional[str] = None,
                         destino: Optional[Path] = None) -> List[Path]:
    """Punto de entrada: sincroniza el datalake desde Drive segun DRIVE_TIPO.

    Devuelve la lista de archivos descargados. El pipeline luego localiza el
    HTML/CSV mas reciente con fetch.localizar_html_mas_reciente().
    """
    tipo = (tipo or config.DRIVE_TIPO).lower()
    print(f"Sincronizando datalake desde Drive (tipo={tipo})...")
    if tipo == "file":
        return [descargar_archivo(url, destino)]
    return descargar_carpeta(url, destino)


if __name__ == "__main__":  # pragma: no cover
    descargados = sincronizar_datalake()
    print(f"\n{len(descargados)} archivo(s) descargado(s) en {config.DATALAKE_DIR}")
