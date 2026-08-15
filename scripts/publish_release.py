"""
Script Automatizado para Publicar una Nueva Release en GitHub
============================================================
1. Solicita la nueva versión y notas de cambio.
2. Actualiza updater/version.py automáticamente.
3. Compila el ejecutable (.exe) sin consola y con DLLs.
4. Sube los cambios de código a GitHub (git add, commit, push).
5. Publica la nueva Release en GitHub con el archivo .exe adjunto.
"""

import os
import sys
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()

# Asegurar encoding UTF-8 en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_current_version() -> str:
    version_file = ROOT_DIR / "updater" / "version.py"
    if not version_file.exists():
        return "v1.0.0"
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else "v1.0.0"


def update_version_file(new_version: str):
    version_file = ROOT_DIR / "updater" / "version.py"
    content = version_file.read_text(encoding="utf-8")
    new_content = re.sub(r'APP_VERSION\s*=\s*["\'][^"\']+["\']', f'APP_VERSION = "{new_version}"', content)
    version_file.write_text(new_content, encoding="utf-8")
    print(f"[OK] updater/version.py actualizado a: {new_version}")


import shutil


def find_executable(name: str) -> str:
    """Busca un ejecutable considerando rutas conocidas en Windows si no está en PATH."""
    # 1. Búsqueda estándar
    found = shutil.which(name)
    if found:
        return found
    
    # 2. Rutas conocidas comunes en Windows
    known_paths = {
        "gh": [
            r"C:\Program Files\GitHub CLI\gh.exe",
            r"C:\Program Files (x86)\GitHub CLI\gh.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"),
        ],
        "git": [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files\Git\bin\git.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        ]
    }
    
    for p in known_paths.get(name.lower(), []):
        if os.path.exists(p):
            return p
            
    return name


def run_cmd(cmd, check=True):
    # Asegurar que PATH incluya rutas de usuario y sistema para 'gh' y 'git'
    env = os.environ.copy()
    if sys.platform == "win32":
        extra_paths = [
            r"C:\Program Files\GitHub CLI",
            r"C:\Program Files\Git\cmd",
            r"C:\Program Files\Git\bin",
        ]
        current_path = env.get("PATH", "")
        env["PATH"] = ";".join(extra_paths) + ";" + current_path

    # Resolver nombre de ejecutable al inicio de la lista
    resolved_cmd = list(cmd) if isinstance(cmd, list) else cmd
    if isinstance(resolved_cmd, list) and len(resolved_cmd) > 0:
        resolved_cmd[0] = find_executable(resolved_cmd[0])

    cmd_str = ' '.join(resolved_cmd) if isinstance(resolved_cmd, list) else str(resolved_cmd)
    print(f"\n[RUN] {cmd_str}")
    
    res = subprocess.run(resolved_cmd, cwd=ROOT_DIR, env=env, shell=False)
    if check and res.returncode != 0:
        print(f"\n[ERROR] El comando falló con código {res.returncode}")
        sys.exit(res.returncode)
    return res


def main():
    print("=" * 65)
    print(" 🚀 PUBLICADOR AUTOMÁTICO DE RELEASES EN GITHUB")
    print("=" * 65)

    curr_ver = get_current_version()
    print(f"\n📌 Versión actual del bot: {curr_ver}\n")

    # 1. Preguntar nueva versión
    new_ver = input(f"Ingresa la NUEVA versión (ejemplo: v1.2.0) [Dejar vacío para '{curr_ver}']: ").strip()
    if not new_ver:
        new_ver = curr_ver
    if not new_ver.startswith("v") and not new_ver.startswith("V"):
        new_ver = f"v{new_ver}"

    # 2. Preguntar título y notas
    default_title = f"{new_ver} - Nuevas mejoras y funcionalidades"
    title_input = input(f"Título de la release [Dejar vacío para '{default_title}']: ").strip()
    release_title = title_input if title_input else default_title

    print("\nEscribe las notas de la versión / changelog (puedes dejar vacío para notas automáticas):")
    notes_input = input("> ").strip()
    if not notes_input:
        notes_input = f"Actualización a {new_ver} con nuevas mejoras de interfaz, estabilidad y rendimiento."

    # 3. Actualizar archivo de versión si cambió
    update_version_file(new_ver)

    # 4. Compilar el nuevo .exe
    print("\n" + "=" * 65)
    print(" 🛠️ PASO 1/3: Compilando nuevo .exe...")
    print("=" * 65)
    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    from build_exe import build_executable
    build_executable()

    exe_path = ROOT_DIR / "dist" / "TikTokRequestBot.exe"
    if not exe_path.exists():
        print(f"[ERROR] No se encontró el ejecutable en: {exe_path}")
        sys.exit(1)

    # 5. Git commit y push
    print("\n" + "=" * 65)
    print(" 📦 PASO 2/3: Guardando y subiendo código a GitHub...")
    print("=" * 65)
    run_cmd(["git", "add", "."])
    run_cmd(["git", "commit", "-m", f"{new_ver} - {release_title}"], check=False)
    run_cmd(["git", "push", "origin", "main"])

    # 6. Publicar Release en GitHub con el .exe
    print("\n" + "=" * 65)
    print(f" 🌐 PASO 3/3: Publicando Release {new_ver} en GitHub...")
    print("=" * 65)
    
    # Si ya existía el tag de release, borrarlo para sobreescribir limpiamente
    run_cmd(["gh", "release", "delete", new_ver, "--repo", "AlvaroJesusC/TikTokRequestBot", "--yes", "--cleanup-tag"], check=False)

    # Crear release con el asset .exe adjunto
    run_cmd([
        "gh", "release", "create", new_ver,
        str(exe_path),
        "--repo", "AlvaroJesusC/TikTokRequestBot",
        "--title", release_title,
        "--notes", notes_input
    ])

    print("\n" + "=" * 65)
    print(f" 🎉 ¡RELEASE {new_ver} PUBLICADA CON ÉXITO!")
    print(f" 🔗 Link: https://github.com/AlvaroJesusC/TikTokRequestBot/releases/tag/{new_ver}")
    print("=" * 65)
    print("💡 Tus amigos recibirán la notificación de actualización automáticamente al abrir su app!\n")


if __name__ == "__main__":
    main()
