"""
Módulo de Descarga e Instalación en Caliente de Actualizaciones
==============================================================
Descarga el nuevo ejecutable con reporte de progreso y ejecuta el script
de reemplazo 'updater.bat' para reiniciar la aplicación con la nueva versión.
"""

import os
import sys
import time
import requests
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable, Optional

from .checker import is_running_as_exe


def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> Optional[Path]:
    """
    Descarga el archivo de actualización a la carpeta '.updater_temp'.
    
    :param download_url: URL directa al asset (.exe o .zip).
    :param progress_callback: Función llamada con (descargados_bytes, total_bytes, porcentaje_0_a_1).
    :param cancel_flag: Función que devuelve True si el usuario canceló la descarga.
    :return: Path al archivo temporal descargado o None si falló/se canceló.
    """
    temp_dir = Path(".updater_temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / "latest_update.tmp"

    try:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass

        headers = {"User-Agent": "TikTokRequestBot-Updater"}
        response = requests.get(download_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        total_bytes = int(response.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 64 * 1024  # 64 KB

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if cancel_flag and cancel_flag():
                    f.close()
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                    return None

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        percent = (downloaded / total_bytes) if total_bytes > 0 else 0.0
                        progress_callback(downloaded, total_bytes, percent)

        return temp_file

    except Exception as e:
        print(f"[UPDATER] Error durante la descarga: {e}")
        return None


def apply_update_and_restart(temp_downloaded_path: Path):
    """
    Crea el script 'updater.bat' para reemplazar el ejecutable bloqueado por Windows,
    inicia la nueva versión y cierra el proceso actual.
    """
    if not is_running_as_exe():
        print("[UPDATER] Modo desarrollo: Abriendo carpeta con la descarga...")
        return

    current_exe = Path(sys.executable).resolve()
    current_dir = current_exe.parent
    temp_file = Path(temp_downloaded_path).resolve()
    current_pid = os.getpid()

    bat_content = f"""@echo off
chcp 65001 > nul
echo ========================================================
echo   ACTUALIZANDO TIKTOK LIVE SONGBOT A LA NUEVA VERSION
echo ========================================================
echo Esperando que el proceso actual finalice...

timeout /t 2 /nobreak > nul

:WAIT_PID
tasklist /FI "PID eq {current_pid}" 2>NUL | find /I "{current_pid}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak > nul
    goto WAIT_PID
)

echo Esperando liberación de archivos de sistema...
timeout /t 1 /nobreak > nul

echo Reemplazando ejecutable principal...
move /Y "{temp_file}" "{current_exe}"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] No se pudo reemplazar el ejecutable.
    echo Asegurate de no tener multiples instancias abiertas.
    pause
    exit /b 1
)

echo Iniciando nueva version...
timeout /t 1 /nobreak > nul
cd /d "{current_dir}"
start "" "{current_exe}"

echo Limpieza finalizada.
del "%~f0"
"""

    bat_path = Path("updater.bat").resolve()
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # Iniciar el script batch en un proceso independiente de Windows
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

    # Cerrar proceso de Python de inmediato
    sys.exit(0)


def open_release_page_in_browser(html_url: str):
    """Abre el navegador web en la página de la versión de GitHub."""
    webbrowser.open(html_url)
