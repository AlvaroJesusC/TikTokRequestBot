"""
Reproductor de YouTube Exclusivo en Formato MP3 (Solo Audio Puro sin Ventanas)
==============================================================================
1. Descarga y extrae audio estrictamente en formato MP3 puro mediante yt-dlp y FFmpeg.
2. Reproduce de forma 100% nativa y headless con Pygame Mixer (CERO ventanas emergentes).
3. Ciclo de vida inteligente: Las canciones se eliminan automáticamente del disco
   inmediatamente después de reproducirse, protegiendo 100% las canciones en espera.
4. CERO retrasos por re-descarga: Las canciones en cola nunca se borran antes de su turno.
"""

import os
import sys
import time
import threading
import shutil
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Union

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import yt_dlp

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    try:
        import pygame_ce as pygame
        _PYGAME_AVAILABLE = True
    except ImportError:
        _PYGAME_AVAILABLE = False

from player.base import BaseAudioPlayer


class YouTubeAudioPlayer(BaseAudioPlayer):
    """Reproductor de solo audio en formato MP3 nativo con eliminación automática post-reproducción."""

    def __init__(
        self,
        cache_dir: str = "./data/cache/audio",
        initial_volume: float = 0.8
    ):
        super().__init__()
        self.cache_dir = Path(cache_dir).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.volume = max(0.0, min(1.0, initial_volume))

        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self._start_time: float = 0.0
        self._paused_time: float = 0.0
        self._accumulated_pause_duration: float = 0.0
        self._stop_requested: bool = False
        self._playback_lock = threading.RLock()

        self._init_audio_engine()

        self._running = True
        self._monitor_thread = threading.Thread(target=self._playback_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _init_audio_engine(self) -> None:
        """Inicializa Pygame Mixer para reproducción de audio puro sin ventanas."""
        if not _PYGAME_AVAILABLE:
            print("[YT_PLAYER] ⚠️ Pygame no está disponible en el entorno.")
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.music.set_volume(self.volume)
        except Exception as e:
            print(f"[YT_PLAYER] Error al inicializar audio mixer: {e}")

    def _clean_query(self, raw_query: str) -> str:
        clean = raw_query.strip()
        for prefix in ["!play", "!song", "!cancion", "!musica", "!pedir"]:
            if clean.lower().startswith(prefix):
                clean = clean[len(prefix):].strip()
        return clean

    def delete_track_file(self, track_or_path: Union[Dict[str, Any], str], protected_filepaths: Optional[Set[str]] = None) -> bool:
        """
        Elimina el archivo MP3 del disco una vez que ha terminado de sonar,
        verificando que no esté todavía en la cola de espera para otra solicitud.
        """
        if not track_or_path:
            return False

        if isinstance(track_or_path, dict):
            filepath = track_or_path.get("filepath")
        else:
            filepath = str(track_or_path)

        if not filepath:
            return False

        abs_path = os.path.abspath(filepath)

        # Si el archivo está protegido (por ejemplo, sigue en la cola para otro usuario), no borrarlo
        if protected_filepaths and abs_path in protected_filepaths:
            return False

        # Solo borrar archivos que estén dentro de la carpeta de caché de audio
        try:
            path_obj = Path(abs_path)
            if self.cache_dir in path_obj.parents or path_obj.parent == self.cache_dir:
                if path_obj.exists():
                    # Asegurarse de que pygame no tenga el archivo bloqueado
                    if _PYGAME_AVAILABLE and pygame.mixer.get_init():
                        if hasattr(pygame.mixer.music, "unload"):
                            try:
                                pygame.mixer.music.unload()
                            except Exception:
                                pass
                    time.sleep(0.05)
                    try:
                        path_obj.unlink(missing_ok=True)
                        print(f"[CACHE] 🗑️ Canción eliminada de caché: {path_obj.name}")
                        return True
                    except PermissionError:
                        # Si Windows mantiene el archivo retenido un instante, ignorar de forma segura
                        pass
        except Exception:
            pass

        return False

    def cleanup_orphaned_cache(self, protected_filepaths: Optional[Set[str]] = None) -> int:
        """
        Elimina cualquier archivo huérfano en la carpeta de caché que no pertenezca
        a la canción en reproducción ni a ninguna canción activa en la cola.
        """
        protected = protected_filepaths or set()
        if self.current_track and self.current_track.get("filepath"):
            protected.add(os.path.abspath(self.current_track["filepath"]))

        deleted_count = 0
        try:
            for f in self.cache_dir.iterdir():
                if f.is_file():
                    abs_f = os.path.abspath(str(f))
                    if abs_f not in protected:
                        try:
                            f.unlink(missing_ok=True)
                            deleted_count += 1
                        except Exception:
                            pass
            if deleted_count > 0:
                print(f"[CACHE] 🧹 Limpieza de huérfanos: {deleted_count} archivos eliminados.")
        except Exception as e:
            print(f"[CACHE] Error en limpieza de huérfanos: {e}")

        return deleted_count

    def clear_all_cache(self) -> int:
        """Elimina todos los archivos de caché excepto el que esté sonando."""
        current_playing_file = None
        if self.current_track and self.current_track.get("filepath"):
            current_playing_file = os.path.abspath(self.current_track["filepath"])

        deleted = 0
        for f in self.cache_dir.iterdir():
            if f.is_file():
                if current_playing_file and os.path.abspath(str(f)) == current_playing_file:
                    continue
                try:
                    f.unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    pass
        print(f"[CACHE] 🧹 Caché vaciada: {deleted} archivos eliminados.")
        return deleted

    def get_cache_stats(self) -> Dict[str, Any]:
        count = 0
        total_bytes = 0
        for f in self.cache_dir.iterdir():
            if f.is_file():
                count += 1
                total_bytes += f.stat().st_size
        return {
            "count": count,
            "size_mb": round(total_bytes / (1024 * 1024), 2)
        }

    def get_ffmpeg_dir(self) -> Optional[str]:
        """Obtiene el directorio donde reside ffmpeg.exe (empaquetado o en sistema)."""
        # 1. En ejecutable empaquetado (PyInstaller _MEIPASS)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundled = Path(sys._MEIPASS) / "ffmpeg.exe"
            if bundled.exists():
                return str(sys._MEIPASS)

        # 2. En carpeta local data/bin
        local_bin = Path("./data/bin/ffmpeg.exe").resolve()
        if local_bin.exists():
            return str(local_bin.parent)

        # 3. En PATH del sistema
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return str(Path(system_ffmpeg).resolve().parent)

        return None

    def ensure_ffmpeg(self) -> Optional[str]:
        """Garantiza que FFmpeg esté disponible, descargando una versión portátil si falta."""
        existing = self.get_ffmpeg_dir()
        if existing:
            return existing

        bin_dir = Path("./data/bin").resolve()
        bin_dir.mkdir(parents=True, exist_ok=True)
        target_exe = bin_dir / "ffmpeg.exe"

        if target_exe.exists():
            return str(bin_dir)

        print("[YT_PLAYER] 📥 Descargando motor FFmpeg portátil para conversión de audio MP3 (una sola vez)...")
        try:
            zip_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            temp_zip = bin_dir / "ffmpeg_temp.zip"
            
            headers = {"User-Agent": "TikTokRequestBot"}
            req = urllib.request.Request(zip_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, "wb") as out_file:
                shutil.copyfileobj(resp, out_file)

            # Extraer solo ffmpeg.exe
            with zipfile.ZipFile(temp_zip, "r") as zf:
                for member in zf.namelist():
                    if member.endswith("ffmpeg.exe"):
                        with zf.open(member) as source, open(target_exe, "wb") as target:
                            shutil.copyfileobj(source, target)
                        break

            if temp_zip.exists():
                temp_zip.unlink()

            if target_exe.exists():
                print(f"[YT_PLAYER] ✅ Motor FFmpeg instalado correctamente en: {target_exe}")
                return str(bin_dir)
        except Exception as e:
            print(f"[YT_PLAYER] ⚠️ No se pudo descargar FFmpeg automáticamente: {e}")

        return None

    def search_track(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Busca y descarga estrictamente en formato MP3 puro.
        Si la canción ya está en disco (descargada previamente), la reutiliza al instante.
        """
        clean_query = self._clean_query(query)
        if not clean_query:
            return None

        ffmpeg_dir = self.ensure_ffmpeg()

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.cache_dir / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "mweb", "android"]
                }
            }
        }

        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = ffmpeg_dir
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        search_queries = [f"ytsearch1:{clean_query}", f"ytsearch1:{clean_query} audio", f"ytsearch1:{clean_query} lyrics"]

        for sq in search_queries:
            try:
                print(f"[YT_PLAYER] 🔍 Buscando/descargando audio MP3 de YouTube: '{clean_query}'...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(sq, download=True)
                    if not info or "entries" not in info or not info["entries"]:
                        continue

                    video = info["entries"][0]
                    video_id = video.get("id")

                    # Archivo MP3 generado
                    mp3_path = str((self.cache_dir / f"{video_id}.mp3").resolve())
                    
                    # Si por alguna razón no se convirtió, buscar archivo coincidente
                    if not os.path.exists(mp3_path):
                        for f in self.cache_dir.glob(f"{video_id}.*"):
                            mp3_path = str(f.resolve())
                            break

                    if os.path.exists(mp3_path):
                        return {
                            "id": video_id,
                            "title": video.get("title", clean_query),
                            "artist": video.get("uploader") or video.get("channel") or "YouTube",
                            "duration": float(video.get("duration") or 0.0),
                            "thumbnail": video.get("thumbnail", ""),
                            "filepath": mp3_path,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "source": "youtube"
                        }
            except Exception as e:
                print(f"[YT_PLAYER] Nota durante búsqueda '{sq}': {e}")
                continue

        print(f"[YT_PLAYER] ❌ No se pudo descargar audio para '{clean_query}'.")
        return None

    def play(self, track_info: Dict[str, Any]) -> bool:
        """Reproduce audio MP3 puramente en segundo plano (0 ventanas emergentes)."""
        if not _PYGAME_AVAILABLE:
            print("[YT_PLAYER] Pygame no está disponible.")
            return False

        filepath = track_info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            query = track_info.get("title") or track_info.get("query")
            found = self.search_track(query)
            if found:
                track_info.update(found)
                filepath = found.get("filepath")

        if not filepath or not os.path.exists(filepath):
            return False

        abs_path = os.path.abspath(filepath)

        with self._playback_lock:
            try:
                self._stop_requested = False
                self._init_audio_engine()

                # Detener y descargar pista anterior para liberar archivo en Windows
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    if hasattr(pygame.mixer.music, "unload"):
                        try:
                            pygame.mixer.music.unload()
                        except Exception:
                            pass
                    time.sleep(0.05)

                    pygame.mixer.music.load(abs_path)
                    pygame.mixer.music.set_volume(self.volume)
                    pygame.mixer.music.play()

                    self.current_track = track_info
                    self.is_playing = True
                    self.is_paused = False
                    self._start_time = time.time()
                    self._accumulated_pause_duration = 0.0

                    print(f"[YT_PLAYER] 🔊 Sonando en segundo plano (MP3): {track_info.get('title')}")
                    return True
            except Exception as e:
                print(f"[YT_PLAYER] Error al reproducir audio MP3 '{abs_path}': {e}")
                self.is_playing = False
                self.current_track = None

        return False

    def pause(self) -> bool:
        with self._playback_lock:
            if not _PYGAME_AVAILABLE or not self.is_playing or self.is_paused:
                return False
            try:
                pygame.mixer.music.pause()
                self.is_paused = True
                self._paused_time = time.time()
                return True
            except Exception:
                return False

    def resume(self) -> bool:
        with self._playback_lock:
            if not _PYGAME_AVAILABLE or not self.is_playing or not self.is_paused:
                return False
            try:
                pygame.mixer.music.unpause()
                self.is_paused = False
                if self._paused_time > 0:
                    self._accumulated_pause_duration += (time.time() - self._paused_time)
                    self._paused_time = 0.0
                return True
            except Exception:
                return False

    def skip(self) -> bool:
        print("[YT_PLAYER] Saltando pista de audio...")
        self.stop()
        self._trigger_track_end()
        return True

    def stop(self) -> bool:
        with self._playback_lock:
            self._stop_requested = True
            if _PYGAME_AVAILABLE and pygame.mixer.get_init():
                try:
                    pygame.mixer.music.stop()
                    if hasattr(pygame.mixer.music, "unload"):
                        pygame.mixer.music.unload()
                except Exception:
                    pass
            self.is_playing = False
            self.is_paused = False
            self.current_track = None
        return True

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
        if _PYGAME_AVAILABLE and pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def get_volume(self) -> float:
        return self.volume

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        return self.current_track

    def get_status(self) -> Dict[str, Any]:
        current_time = 0.0
        duration = 0.0
        if self.current_track:
            duration = float(self.current_track.get("duration", 0.0))
            if self.is_playing:
                if self.is_paused:
                    current_time = max(0.0, self._paused_time - self._start_time - self._accumulated_pause_duration)
                else:
                    current_time = max(0.0, time.time() - self._start_time - self._accumulated_pause_duration)
                if duration > 0:
                    current_time = min(current_time, duration)

        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_time": round(current_time, 1),
            "duration": round(duration, 1),
            "volume": round(self.volume, 2),
            "current_track": self.current_track,
            "source": "youtube"
        }

    def _playback_monitor_loop(self) -> None:
        while self._running:
            time.sleep(0.5)
            if self.is_playing and not self.is_paused and not self._stop_requested:
                if _PYGAME_AVAILABLE and pygame.mixer.get_init():
                    elapsed = time.time() - self._start_time - self._accumulated_pause_duration
                    # Si el mixer ya no está busy y ha pasado al menos 1 segundo
                    if not pygame.mixer.music.get_busy() and elapsed > 1.0:
                        print("[YT_PLAYER] Pista MP3 finalizada con éxito.")
                        self.stop()
                        self._trigger_track_end()
