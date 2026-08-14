"""
Módulo de Comprobación de Actualizaciones en GitHub
===================================================
Consulta la API pública de GitHub para detectar nuevas versiones y notas de la versión.
"""

import sys
import requests
from typing import Dict, Any, Optional

try:
    from packaging import version
except ImportError:
    version = None

from .version import APP_VERSION, APP_NAME, RELEASES_API_URL, REPO_URL


def is_running_as_exe() -> bool:
    """Verifica si la aplicación se está ejecutando como un .exe congelado por PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def parse_version_str(v_str: str):
    """Limpia y normaliza el string de versión (ej. 'v1.0.1' -> '1.0.1')."""
    cleaned = v_str.strip().lstrip("v").lstrip("V")
    if version:
        try:
            return version.parse(cleaned)
        except Exception:
            pass
    # Fallback básico para tuplas numéricas (ej. (1, 0, 1))
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_updates() -> Dict[str, Any]:
    """
    Consulta GitHub Releases para verificar si hay una nueva versión.
    Retorna un diccionario con los detalles de la actualización.
    """
    result: Dict[str, Any] = {
        "has_update": False,
        "current_version": APP_VERSION,
        "latest_version": APP_VERSION,
        "release_title": "",
        "release_notes": "",
        "download_url": "",
        "asset_name": "",
        "asset_size_mb": 0.0,
        "html_url": REPO_URL,
        "is_exe": is_running_as_exe(),
        "error": None
    }

    try:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{APP_NAME}-Updater"
        }
        
        response = requests.get(RELEASES_API_URL, headers=headers, timeout=6)
        
        if response.status_code == 404:
            # Aún no hay ninguna release publicada en GitHub
            return result

        if response.status_code != 200:
            result["error"] = f"GitHub API respondió con código {response.status_code}"
            return result

        data = response.json()
        raw_tag = data.get("tag_name", "").strip()
        if not raw_tag:
            return result

        current_v = parse_version_str(APP_VERSION)
        latest_v = parse_version_str(raw_tag)

        # Comparar si la versión remota es superior
        has_new = False
        try:
            has_new = latest_v > current_v
        except Exception:
            has_new = raw_tag != APP_VERSION

        if has_new:
            result["has_update"] = True
            result["latest_version"] = raw_tag
            result["release_title"] = data.get("name", raw_tag)
            result["release_notes"] = data.get("body", "No se proporcionaron notas de versión.")
            result["html_url"] = data.get("html_url", REPO_URL)

            # Buscar asset .exe o .zip para descarga directa
            assets = data.get("assets", [])
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    result["download_url"] = asset.get("browser_download_url", "")
                    result["asset_name"] = asset.get("name", "")
                    size_bytes = asset.get("size", 0)
                    result["asset_size_mb"] = round(size_bytes / (1024 * 1024), 2)
                    break
                elif name.endswith(".zip") and not result["download_url"]:
                    result["download_url"] = asset.get("browser_download_url", "")
                    result["asset_name"] = asset.get("name", "")
                    size_bytes = asset.get("size", 0)
                    result["asset_size_mb"] = round(size_bytes / (1024 * 1024), 2)

    except requests.exceptions.RequestException as req_err:
        result["error"] = f"Error de conexión: {req_err}"
    except Exception as e:
        result["error"] = f"Error inesperado: {e}"

    return result
