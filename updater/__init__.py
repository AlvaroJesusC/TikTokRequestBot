"""
Paquete del Sistema de Actualizaciones Automáticas
==================================================
Maneja la comprobación de versiones en GitHub Releases, descarga
e instalación en caliente para ejecutables de Windows.
"""

from .version import (
    APP_VERSION,
    APP_NAME,
    GITHUB_OWNER,
    GITHUB_REPO,
    REPO_URL,
    RELEASES_API_URL
)
from .checker import check_for_updates, is_running_as_exe
from .installer import download_update, apply_update_and_restart, open_release_page_in_browser
from .ui import UpdateModalDialog, check_updates_background

__all__ = [
    "APP_VERSION",
    "APP_NAME",
    "GITHUB_OWNER",
    "GITHUB_REPO",
    "REPO_URL",
    "RELEASES_API_URL",
    "check_for_updates",
    "is_running_as_exe",
    "download_update",
    "apply_update_and_restart",
    "open_release_page_in_browser",
    "UpdateModalDialog",
    "check_updates_background"
]
