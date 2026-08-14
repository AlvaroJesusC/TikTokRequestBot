"""
Orquestador Central de TikTok LIVE y Control de Reproducción
===========================================================
Garantiza transiciones de audio 100% limpias:
1. Elimina solapamientos de canciones mediante un cerrojo de reproducción (threading.Lock).
2. Salta canciones inmediatamente con !skip o el botón de skip de la app.
3. Procesa descargas en segundo plano protegiendo 100% todas las canciones en cola.
4. Auto-elimina automáticamente el archivo MP3 del disco una vez reproducida la canción.
"""

import os
import asyncio
import threading
import time
from typing import Optional, Callable, Dict, Any, List, Set
from datetime import datetime

from bot.command_parser import CommandParser
from bot.queue_manager import QueueManager
from bot.permissions import PermissionManager
from player.base import BaseAudioPlayer
from player.youtube_player import YouTubeAudioPlayer
from player.spotify_player import SpotifyOAuthPlayer
from player.local_file_player import LocalFileAudioPlayer

try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent
    _TIKTOK_AVAILABLE = True
except ImportError:
    _TIKTOK_AVAILABLE = False


class LiveBotOrchestrator:
    def __init__(
        self,
        youtube_player: YouTubeAudioPlayer,
        spotify_player: SpotifyOAuthPlayer,
        local_player: LocalFileAudioPlayer,
        queue_manager: QueueManager,
        permission_manager: PermissionManager,
        config: Dict[str, Any]
    ):
        self.youtube_player = youtube_player
        self.spotify_player = spotify_player
        self.local_player = local_player
        self.queue_manager = queue_manager
        self.permissions = permission_manager
        self.config = config
        self.parser = CommandParser()

        self.player_mode = config.get("player_mode", "youtube")
        self._playback_lock = threading.RLock()

        # Control de comandos activos/deshabilitados desde la interfaz
        self.enabled_commands: Dict[str, bool] = {
            "play": True,
            "skip": True,
            "pause": True,
            "clear": True
        }

        self.client: Optional[Any] = None
        self.status = "DISCONNECTED"
        self.current_unique_id = config.get("tiktok", {}).get("unique_id", "")
        self.euler_api_key = config.get("tiktok", {}).get("euler_api_key", "")

        # Callbacks para la GUI de escritorio
        self.on_log_callback: Optional[Callable[[str, str], None]] = None
        self.on_status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_comment_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_queue_update_callback: Optional[Callable[[], None]] = None
        self.on_player_update_callback: Optional[Callable[[], None]] = None

        # Callbacks de fin de pista
        self.youtube_player.set_on_track_end_callback(self._handle_track_end)
        self.local_player.set_on_track_end_callback(self._handle_track_end)
        self.spotify_player.set_on_track_end_callback(self._handle_track_end)

        # Limpiar huérfanos al inicio (archivos que no están en cola)
        self.youtube_player.cleanup_orphaned_cache(self._get_active_queued_filepaths())

        self._task: Optional[asyncio.Task] = None

    @property
    def current_player(self) -> BaseAudioPlayer:
        if self.player_mode == "spotify":
            return self.spotify_player
        elif self.player_mode == "youtube":
            return self.youtube_player
        return self.local_player

    def _get_active_queued_filepaths(self) -> Set[str]:
        """Devuelve el conjunto de rutas absolutas protegidas (en cola activa)."""
        paths = set()
        for item in self.queue_manager.get_queue():
            track = item.get("track", {})
            fp = track.get("filepath")
            if fp:
                paths.add(os.path.abspath(fp))
        return paths

    def set_command_enabled(self, command_name: str, enabled: bool) -> None:
        """Activa o desactiva un comando específico desde la interfaz."""
        self.enabled_commands[command_name] = enabled
        estado = "HABILITADO" if enabled else "DESHABILITADO"
        self.log("system", f"⚙️ Comando '!{command_name}' {estado} para el chat.")

    def set_player_mode(self, mode: str) -> None:
        if mode in ["spotify", "youtube", "local"]:
            self.player_mode = mode
            self.log("info", f"Motor de reproducción cambiado a: {mode.upper()}")
            self._notify_player_update()

    def log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] {message}")
        if self.on_log_callback:
            try:
                self.on_log_callback(level, f"[{timestamp}] {message}")
            except Exception:
                pass

    def _set_status(self, new_status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.status = new_status
        payload = {"status": new_status, "unique_id": self.current_unique_id}
        if extra:
            payload.update(extra)
        if self.on_status_callback:
            try:
                self.on_status_callback(new_status, payload)
            except Exception:
                pass

    async def connect(self, unique_id: str, euler_key: str = "") -> bool:
        """Conecta con el chat de TikTok LIVE."""
        if not _TIKTOK_AVAILABLE:
            self.log("error", "Librería TikTokLive no instalada.")
            self._set_status("ERROR", {"error": "TikTokLive no instalado"})
            return False

        clean_id = unique_id.strip().lstrip("@")
        if not clean_id:
            self.log("error", "Nombre de usuario de TikTok inválido.")
            return False

        await self.disconnect()

        self.current_unique_id = clean_id
        self.euler_api_key = euler_key.strip()
        self._set_status("CONNECTING")
        self.log("info", f"Conectando al chat de @{clean_id}...")

        client_kwargs = {"unique_id": f"@{clean_id}"}
        if self.euler_api_key:
            client_kwargs["sign_api_key"] = self.euler_api_key

        try:
            self.client = TikTokLiveClient(**client_kwargs)
            self._register_events()
            self._task = asyncio.create_task(self._run_client())
            return True
        except Exception as e:
            self.log("error", f"Error al inicializar cliente TikTokLive: {e}")
            self._set_status("ERROR", {"error": str(e)})
            return False

    async def disconnect(self) -> None:
        if self.client:
            try:
                if hasattr(self.client, "disconnect"):
                    await self.client.disconnect()
            except Exception:
                pass
            self.client = None

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._set_status("DISCONNECTED")
        self.log("info", "Desconectado de TikTok LIVE.")

    async def _run_client(self) -> None:
        try:
            await self.client.start()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log("error", f"Desconexión del chat: {e}")
            self._set_status("OFFLINE", {"error": str(e)})

    def _register_events(self) -> None:
        if not self.client:
            return

        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            self._set_status("CONNECTED")
            self.log("success", f"🟢 ¡Conectado con éxito al chat de @{self.current_unique_id}!")

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            self._set_status("DISCONNECTED")
            self.log("warning", "El directo de TikTok ha finalizado o se ha desconectado.")

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            user = event.user.unique_id
            nickname = event.user.nickname
            comment = event.comment

            if self.on_comment_callback:
                try:
                    self.on_comment_callback({
                        "user": user,
                        "nickname": nickname,
                        "comment": comment,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                except Exception:
                    pass

            self._process_chat_command(comment, user, nickname)

    def _process_chat_command(self, comment: str, user: str, nickname: str) -> None:
        """
        Filtro estricto: ÚNICAMENTE los comentarios que empiecen por '!play '
        serán interpretados como solicitudes de canciones si el comando está habilitado.
        """
        raw_text = comment.strip()
        if not raw_text.startswith("!"):
            return

        parts = raw_text.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        # 1. SOLICITUD ESTRICTA CON !play
        if cmd == "!play":
            if not self.enabled_commands.get("play", True):
                self.log("warning", f"⛔ @{user} intentó usar !play (Comando deshabilitado por el streamer).")
                return

            if not args:
                self.log("warning", f"⚠️ @{user} usó !play sin especificar canción. Ejemplo: !play awake wrld")
                return

            # MODO YOUTUBE (Auto / Headless)
            if self.player_mode == "youtube":
                self.log("info", f"🔍 [CHAT !play] @{user} pidió: '{args}' (Buscando en YouTube)...")
                threading.Thread(
                    target=self._async_handle_youtube_request,
                    args=(args, user, nickname),
                    daemon=True
                ).start()

            # MODO SPOTIFY
            elif self.player_mode == "spotify":
                if not self.spotify_player.is_linked:
                    self.log("warning", "⚠️ Spotify no está vinculado. Haz clic en '🔗 Vincular Spotify'.")
                    return

                self.log("song", f"🎵 [CHAT !play] Spotify: @{user} pidió '{args}' -> Reproduciendo...")
                threading.Thread(
                    target=self.spotify_player.search_and_play,
                    args=(args,),
                    daemon=True
                ).start()
                self._notify_player_update()

            # MODO LOCAL
            else:
                match, score = self.parser.find_best_match(args, self.local_player.indexed_tracks)
                if match and score >= 45:
                    self.queue_manager.add(match, user, nickname)
                    self.log("song", f"🎵 [CHAT !play] Local: '{match['title']}' encolada por @{user}")
                    self._notify_queue_update()
                    self._check_and_play_next()
                else:
                    self.log("warning", f"❌ Canción local no encontrada para '{args}'")

        # 2. COMANDOS DE ADMINISTRACIÓN / MODERACIÓN
        elif cmd in ["!skip", "!siguiente", "!next"]:
            if not self.enabled_commands.get("skip", True):
                self.log("warning", f"⛔ @{user} intentó usar !skip (Comando deshabilitado por el streamer).")
                return

            if self.permissions.can_skip(user):
                self.log("admin", f"⏭️ @{user} saltó la canción actual.")
                self.current_player.skip()
                self._notify_player_update()
            else:
                self.log("permission", f"⛔ @{user} no tiene permisos de moderador para saltar canciones.")

        elif cmd in ["!pause", "!pausa"]:
            if not self.enabled_commands.get("pause", True):
                self.log("warning", f"⛔ @{user} intentó usar !pause (Comando deshabilitado por el streamer).")
                return

            if self.permissions.can_control_playback(user):
                self.log("admin", f"⏸️ @{user} pausó la música.")
                self.current_player.pause()
                self._notify_player_update()

        elif cmd in ["!resume", "!reanudar", "!unpause"]:
            if not self.enabled_commands.get("pause", True):
                self.log("warning", f"⛔ @{user} intentó usar !resume (Comando deshabilitado por el streamer).")
                return

            if self.permissions.can_control_playback(user):
                self.log("admin", f"▶️ @{user} reanudó la música.")
                self.current_player.resume()
                self._notify_player_update()

        elif cmd in ["!clear", "!limpiar", "!vaciar"]:
            if not self.enabled_commands.get("clear", True):
                self.log("warning", f"⛔ @{user} intentó usar !clear (Comando deshabilitado por el streamer).")
                return

            if self.permissions.can_clear(user):
                count = self.clear_queue()
                self.log("admin", f"🗑️ @{user} vació la cola ({count} canciones).")
                self._notify_queue_update()

        elif cmd in ["!current", "!actual", "!np"]:
            curr = self.current_player.get_current_track()
            if curr:
                self.log("info", f"🎶 Sonando: {curr.get('title')} - {curr.get('artist')}")

    def _async_handle_youtube_request(self, query: str, user: str, nickname: str) -> None:
        """Descarga y encola la canción en segundo plano, iniciando reproducción solo si no hay otra sonando."""
        track = self.youtube_player.search_track(query)
        if track:
            self.queue_manager.add(track, user, nickname)
            self.log("song", f"🎵 [!play] '{track['title']}' encolada con éxito por @{user}")
            self._notify_queue_update()
            self._check_and_play_next()
        else:
            self.log("warning", f"❌ No se encontró en YouTube '{query}' pedida por @{user}")

    def _check_and_play_next(self) -> None:
        with self._playback_lock:
            if not self.current_player.is_playing:
                self._play_next_in_queue()

    def _handle_track_end(self) -> None:
        """Maneja el fin de pista: registra en historial y auto-elimina del disco el MP3 reproducido."""
        curr = self.current_player.get_current_track()
        if curr:
            self.queue_manager.add_to_history({"track": curr})
            # Si era de YouTube, eliminar el MP3 reproducido para liberar espacio inmediatamente
            if curr.get("source") == "youtube":
                active_paths = self._get_active_queued_filepaths()
                self.youtube_player.delete_track_file(curr, protected_filepaths=active_paths)

        self._play_next_in_queue()

    def _play_next_in_queue(self) -> None:
        with self._playback_lock:
            next_item = self.queue_manager.pop()
            if next_item:
                track = next_item["track"]
                self.current_player.stop()
                time.sleep(0.08)
                success = self.current_player.play(track)
                if success:
                    self.log("player", f"▶️ Reproduciendo: '{track['title']}' (Pedida por @{next_item['requested_by']})")
                else:
                    self.log("warning", f"❌ Error al reproducir '{track['title']}'")
            else:
                self.current_player.stop()
                self.log("player", "⏹️ Cola finalizada. Esperando nuevos !play.")

            self._notify_queue_update()
            self._notify_player_update()

    def clear_queue(self) -> int:
        """Vacía la cola y elimina los archivos descargados huérfanos de la caché."""
        removed_items = self.queue_manager.get_queue()
        count = self.queue_manager.clear()

        # Proteger la canción que esté sonando en este momento
        current_fp = None
        curr = self.current_player.get_current_track()
        if curr and curr.get("filepath"):
            current_fp = os.path.abspath(curr["filepath"])

        protected = {current_fp} if current_fp else set()
        for item in removed_items:
            track = item.get("track", {})
            if track.get("source") == "youtube":
                self.youtube_player.delete_track_file(track, protected_filepaths=protected)

        return count

    def remove_queue_item_by_id(self, item_id: str) -> bool:
        """Elimina un ítem específico de la cola y su archivo MP3 si no está duplicado."""
        queue_items = self.queue_manager.get_queue()
        target_item = next((it for it in queue_items if it.get("id") == item_id), None)
        success = self.queue_manager.remove_by_id(item_id)
        if success and target_item:
            track = target_item.get("track", {})
            if track.get("source") == "youtube":
                active_paths = self._get_active_queued_filepaths()
                curr = self.current_player.get_current_track()
                if curr and curr.get("filepath"):
                    active_paths.add(os.path.abspath(curr["filepath"]))
                self.youtube_player.delete_track_file(track, protected_filepaths=active_paths)
        return success

    def _notify_queue_update(self) -> None:
        if self.on_queue_update_callback:
            try:
                self.on_queue_update_callback()
            except Exception:
                pass

    def _notify_player_update(self) -> None:
        if self.on_player_update_callback:
            try:
                self.on_player_update_callback()
            except Exception:
                pass
