"""
Controlador de Spotify (Spotipy Connect con Aislamiento Total de Errores)
=========================================================================
Controla Spotify solo cuando el usuario lo solicita explícitamente, sin sondeos
automáticos que generen errores 403 en segundo plano.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from player.base import BaseAudioPlayer

SPOTIFY_SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"


class SpotifyOAuthPlayer(BaseAudioPlayer):
    """Reproductor que utiliza la API oficial de Spotify (Spotipy) con OAuth2."""

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        redirect_uri: str = "http://127.0.0.1:8888/callback",
        cache_path: str = "./data/cache/.spotify_token_cache",
        initial_volume: float = 0.8
    ):
        super().__init__()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.redirect_uri = redirect_uri.strip() or "http://127.0.0.1:8888/callback"
        self.cache_path = str(Path(cache_path).resolve())
        Path(self.cache_path).parent.mkdir(parents=True, exist_ok=True)
        self.volume = max(0.0, min(1.0, initial_volume))

        self.auth_manager: Optional[SpotifyOAuth] = None
        self.sp: Optional[spotipy.Spotify] = None
        self.user_profile: Optional[Dict[str, Any]] = None
        self.is_linked: bool = False

        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.progress_ms: int = 0
        self.duration_ms: int = 0

        self._running = True
        self._init_auth()

    def _init_auth(self) -> None:
        if not self.client_id or not self.client_secret:
            return

        try:
            self.auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=SPOTIFY_SCOPES,
                cache_path=self.cache_path,
                open_browser=False
            )

            token_info = self.auth_manager.get_cached_token()
            if token_info and not self.auth_manager.is_token_expired(token_info):
                self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                self.is_linked = True
        except Exception:
            self.is_linked = False

    def link_account(self) -> bool:
        if not self.client_id or not self.client_secret:
            return False

        try:
            self.auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=SPOTIFY_SCOPES,
                cache_path=self.cache_path,
                open_browser=True
            )

            token = self.auth_manager.get_access_token(as_dict=False)
            if token:
                self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                self.user_profile = {"display_name": "Spotify Conectado"}
                self.is_linked = True
                return True
        except Exception as e:
            print(f"[SPOTIFY_OAUTH] Error durante vinculación: {e}")
            self.is_linked = False

        return False

    def unlink_account(self) -> None:
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except Exception:
                pass
        self.sp = None
        self.user_profile = None
        self.is_linked = False

    def _get_active_device_id(self) -> Optional[str]:
        if not self.sp or not self.is_linked:
            return None
        try:
            devices = self.sp.devices().get("devices", [])
            if not devices:
                return None
            for d in devices:
                if d.get("is_active"):
                    return d.get("id")
            for d in devices:
                if d.get("type", "").lower() == "computer":
                    return d.get("id")
            return devices[0].get("id")
        except Exception:
            return None

    def search_and_play(self, query: str) -> bool:
        if not self.sp or not self.is_linked:
            return False

        clean_query = query.strip()
        for prefix in ["!play", "!song", "!cancion", "!musica", "!pedir"]:
            if clean_query.lower().startswith(prefix):
                clean_query = clean_query[len(prefix):].strip()

        if not clean_query:
            return self.resume()

        try:
            res = self.sp.search(q=clean_query, type="track", limit=1)
            tracks = res.get("tracks", {}).get("items", [])
            if not tracks:
                return False

            t = tracks[0]
            uri = t.get("uri")
            title = t.get("name")
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            album_art = t.get("album", {}).get("images", [{}])[0].get("url", "")
            duration_sec = round(t.get("duration_ms", 0) / 1000.0, 1)

            device_id = self._get_active_device_id()
            kwargs = {"uris": [uri]}
            if device_id:
                kwargs["device_id"] = device_id

            self.sp.start_playback(**kwargs)

            self.current_track = {
                "id": t.get("id"),
                "title": title,
                "artist": artists,
                "duration": duration_sec,
                "album_art": album_art,
                "uri": uri,
                "source": "spotify"
            }
            self.is_playing = True
            self.is_paused = False
            return True
        except Exception as e:
            print(f"[SPOTIFY_OAUTH] Error al reproducir: {e}")
            return False

    def play(self, track_info: Dict[str, Any]) -> bool:
        uri = track_info.get("uri")
        if uri and self.sp and self.is_linked:
            try:
                device_id = self._get_active_device_id()
                kwargs = {"uris": [uri]}
                if device_id:
                    kwargs["device_id"] = device_id
                self.sp.start_playback(**kwargs)
                self.current_track = track_info
                self.is_playing = True
                self.is_paused = False
                return True
            except Exception:
                pass

        query = track_info.get("title") or track_info.get("query") or ""
        return self.search_and_play(query)

    def pause(self) -> bool:
        if self.sp and self.is_linked:
            try:
                self.sp.pause_playback()
                self.is_paused = True
                self.is_playing = False
                return True
            except Exception:
                pass
        return False

    def resume(self) -> bool:
        if self.sp and self.is_linked:
            try:
                self.sp.start_playback()
                self.is_paused = False
                self.is_playing = True
                return True
            except Exception:
                pass
        return False

    def skip(self) -> bool:
        if self.sp and self.is_linked:
            try:
                self.sp.next_track()
                time.sleep(0.4)
                self._trigger_track_end()
                return True
            except Exception:
                pass
        return False

    def stop(self) -> bool:
        return self.pause()

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
        if self.sp and self.is_linked:
            try:
                vol_int = int(self.volume * 100)
                self.sp.volume(vol_int)
            except Exception:
                pass

    def get_volume(self) -> float:
        return self.volume

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        return self.current_track

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "current_time": round(self.progress_ms / 1000.0, 1),
            "duration": round(self.duration_ms / 1000.0, 1),
            "volume": self.volume,
            "current_track": self.current_track,
            "is_linked": self.is_linked,
            "user_name": self.user_profile.get("display_name") if self.user_profile else "",
            "source": "spotify"
        }
