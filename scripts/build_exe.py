"""
Script de Compilación Automatizada para Generar el Ejecutable (.exe)
===================================================================
Utiliza PyInstaller para empaquetar el bot en un ejecutable independiente para Windows.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()

# Fix encoding para emojis en consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_executable():
    print("=" * 60)
    print(" 🛠️ COMPILADOR DE TIKTOK LIVE SONGBOT (.EXE)")
    print("=" * 60)

    os.chdir(ROOT_DIR)

    # 1. Comprobar si PyInstaller está instalado
    try:
        import PyInstaller
        print(f"[OK] PyInstaller detectado: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller no encontrado. Instalando automáticamente...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Limpiar compilaciones previas
    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"
    for d in [dist_dir, build_dir]:
        if d.exists():
            print(f"[CLEAN] Eliminando carpeta {d.name}...")
            shutil.rmtree(d, ignore_errors=True)

    # 3. Localizar la DLL de Python (necesaria para --onefile en Python 3.14+)
    python_dir = Path(sys.executable).parent
    python_dll = python_dir / f"python{sys.version_info.major}{sys.version_info.minor}.dll"
    
    if python_dll.exists():
        print(f"[OK] Python DLL encontrada: {python_dll}")
    else:
        print(f"[WARN] No se encontró {python_dll.name}, el .exe podría fallar al abrir.")

    # 4. Argumentos de PyInstaller
    # --onefile: Crea un único archivo ejecutable fácil de actualizar y compartir
    # --windowed: Oculta la consola negra de Windows por defecto
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "TikTokRequestBot",
        "--add-binary", f"{python_dll}{os.pathsep}.",
        "--add-data", f"config.example.yaml{os.pathsep}.",
        "--add-data", f"music/LEEME.txt{os.pathsep}music",
        "--collect-all", "customtkinter",
        "--collect-all", "TikTokLive",
        "--hidden-import", "updater",
        "--hidden-import", "player",
        "--hidden-import", "bot",
        "--hidden-import", "gui",
        "main.py"
    ]

    print("\n[BUILD] Compilando con PyInstaller (esto puede tardar 1-2 minutos)...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = dist_dir / "TikTokRequestBot.exe"
        print("\n" + "=" * 60)
        print(" 🎉 ¡COMPILACIÓN EXITOSA!")
        print(f" 📦 Ejecutable generado en: {exe_path}")
        print("=" * 60)
        print("\n💡 Para compartir con tus amigos:")
        print("1. Copia 'TikTokRequestBot.exe' de la carpeta 'dist/'")
        print("2. Junto con el archivo 'config.example.yaml' y la carpeta 'music/'")
        print("3. O súbelo a una Release en tu GitHub para que el auto-actualizador funcione!")
    else:
        print("\n❌ Error durante la compilación con PyInstaller.")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
