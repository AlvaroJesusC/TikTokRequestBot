"""
Punto de Entrada Principal - TikTok LIVE Song Request Bot (App Nativa de Escritorio)
===================================================================================
Inicia los motores de reproducción (YouTube Universal con auto-limpieza de caché,
Spotify Connect Oficial y Música Local), el orquestador y la ventana nativa.
"""

import sys
import os
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from bot.config_manager import load_config
from player.youtube_player import YouTubeAudioPlayer
from player.spotify_player import SpotifyOAuthPlayer
from player.local_file_player import LocalFileAudioPlayer
from bot.queue_manager import QueueManager
from bot.permissions import PermissionManager
from bot.live_bot import LiveBotOrchestrator
from gui.desktop_app import DesktopApp


def main():
    print("=" * 65)
    print(" 🎵 TIKTOK LIVE SONG REQUEST BOT - DESKTOP APP 🎵")
    print("=" * 65)

    config = load_config()
    audio_cfg = config.get("audio", {})
    perm_cfg = config.get("permissions", {})
    spotify_cfg = config.get("spotify", {})

    music_folder = audio_cfg.get("music_folder", "./music")
    default_vol = float(audio_cfg.get("default_volume", 0.8))
    allowed_exts = audio_cfg.get("allowed_extensions", [".mp3", ".wav", ".ogg", ".flac"])

    Path(music_folder).mkdir(parents=True, exist_ok=True)
    Path("./data/cache/audio").mkdir(parents=True, exist_ok=True)

    # 1. Instanciar Motores
    print(f"\n[INIT] Inicializando motor de YouTube MP3 (Auto-limpieza inteligente post-reproducción)...")
    youtube_player = YouTubeAudioPlayer(
        initial_volume=default_vol
    )

    print("[INIT] Inicializando controlador de Spotify...")
    spotify_player = SpotifyOAuthPlayer(
        client_id=spotify_cfg.get("client_id", ""),
        client_secret=spotify_cfg.get("client_secret", ""),
        redirect_uri=spotify_cfg.get("redirect_uri", "http://127.0.0.1:8888/callback"),
        initial_volume=default_vol
    )

    print("[INIT] Inicializando reproductor local...")
    local_player = LocalFileAudioPlayer(
        music_folder=music_folder,
        allowed_extensions=allowed_exts,
        initial_volume=default_vol
    )

    print("[INIT] Inicializando gestor de cola e historial...")
    queue_mgr = QueueManager()

    print("[INIT] Configurando permisos...")
    permissions = PermissionManager(
        streamer_id=perm_cfg.get("streamer_id", ""),
        moderators=perm_cfg.get("moderators", []),
        skip_permission=perm_cfg.get("skip_permission", "mods")
    )

    print("[INIT] Inicializando orquestador central...")
    orchestrator = LiveBotOrchestrator(
        youtube_player=youtube_player,
        spotify_player=spotify_player,
        local_player=local_player,
        queue_manager=queue_mgr,
        permission_manager=permissions,
        config=config
    )

    # 2. Lanzar la Aplicación Nativa
    print("\n🚀 Abriendo aplicación nativa en Windows 11...")
    app = DesktopApp(orchestrator)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Cerrando aplicación...")
        youtube_player.stop()
        local_player.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
