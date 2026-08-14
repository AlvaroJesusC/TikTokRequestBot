"""
Implementación del Reproductor de Audio Local con Pygame / Pygame-CE y Mutagen
==============================================================================
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from player.base import BaseAudioPlayer

# Asegurar importación segura de Pygame / Pygame-CE o Mutagen
try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    try:
        import pygame_ce as pygame
        _PYGAME_AVAILABLE = True
    except ImportError:
        _PYGAME_AVAILABLE = False

try:
    import mutagen
    _MUTAGEN_AVAILABLE = True
except ImportError:
    _MUTAGEN_AVAILABLE = False


class LocalFileAudioPlayer(BaseAudioPlayer):
    """Reproductor de música para archivos locales en disco."""

    def __init__(self, music_folder: str = "./music", allowed_extensions: Optional[List[str]] = None, initial_volume: float = 0.8):
        super().__init__()
        self.music_folder = Path(music_folder).resolve()
        self.allowed_extensions = allowed_extensions or [".mp3", ".wav", ".ogg", ".flac"]
        self.volume = max(0.0, min(1.0, initial_volume))
        
        self.indexed_tracks: List[Dict[str, Any]] = []
        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self._start_time: float = 0.0
        self._paused_time: float = 0.0
        self._accumulated_pause_duration: float = 0.0
        self._stop_requested: bool = False
        
        self._init_pygame()
        self.scan_library()
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._playback_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _init_pygame(self) -> None:
        if not _PYGAME_AVAILABLE:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                pygame.mixer.music.set_volume(self.volume)
        except Exception as e:
            print(f"[PLAYER] Nota: Pygame mixer no inicializado: {e}")

    def scan_library(self) -> int:
        self.music_folder.mkdir(parents=True, exist_ok=True)
        tracks = []
        
        for root, _, files in os.walk(self.music_folder):
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext in self.allowed_extensions:
                    track_data = self._extract_metadata(file_path)
                    tracks.append(track_data)
        
        self.indexed_tracks = tracks
        return len(self.indexed_tracks)

    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        clean_name = file_path.stem
        title = clean_name
        artist = "Desconocido"
        album = ""
        duration = 0.0

        if _MUTAGEN_AVAILABLE:
            try:
                audio = mutagen.File(str(file_path), easy=True)
                if audio is not None:
                    if audio.info and hasattr(audio.info, "length"):
                        duration = float(audio.info.length)
                    if "title" in audio and audio["title"]:
                        title = str(audio["title"][0]).strip()
                    if "artist" in audio and audio["artist"]:
                        artist = str(audio["artist"][0]).strip()
                    if "album" in audio and audio["album"]:
                        album = str(audio["album"][0]).strip()
            except Exception:
                pass

        search_text = f"{title} {artist} {clean_name}".lower()

        return {
            "id": str(hash(str(file_path))),
            "filepath": str(file_path),
            "filename": file_path.name,
            "title": title,
            "artist": artist,
            "album": album,
            "duration": round(duration, 1),
            "search_text": search_text
        }

    def play(self, track_info: Dict[str, Any]) -> bool:
        if not _PYGAME_AVAILABLE:
            print("[PLAYER] Pygame no está disponible para archivos locales.")
            return False

        filepath = track_info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            return False

        try:
            self._stop_requested = False
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            
            self.current_track = track_info
            self.is_playing = True
            self.is_paused = False
            self._start_time = time.time()
            self._accumulated_pause_duration = 0.0
            return True
        except Exception as e:
            print(f"[PLAYER] Error al reproducir '{filepath}': {e}")
            self.is_playing = False
            self.current_track = None
            return False

    def pause(self) -> bool:
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

    def stop(self) -> bool:
        if not _PYGAME_AVAILABLE:
            return False
        try:
            self._stop_requested = True
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_track = None
            return True
        except Exception:
            return False

    def skip(self) -> bool:
        self.stop()
        self._trigger_track_end()
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
            "total_indexed_tracks": len(self.indexed_tracks)
        }

    def _playback_monitor_loop(self) -> None:
        while self._running:
            time.sleep(0.5)
            if self.is_playing and not self.is_paused and not self._stop_requested:
                if _PYGAME_AVAILABLE and pygame.mixer.get_init():
                    elapsed = time.time() - self._start_time - self._accumulated_pause_duration
                    if not pygame.mixer.music.get_busy() and elapsed > 1.0:
                        self.is_playing = False
                        self.current_track = None
                        self._trigger_track_end()
