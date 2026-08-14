"""
Interfaz Abstracta para el Reproductor de Audio
==============================================
Define el contrato estándar que debe cumplir cualquier motor de reproducción
(archivos locales, o futuros adaptadores) sin acoplar la lógica del bot o de la GUI.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any


class BaseAudioPlayer(ABC):
    """Clase base abstracta para el reproductor de audio del bot."""

    def __init__(self):
        self._on_track_end_callback: Optional[Callable[[], None]] = None

    def set_on_track_end_callback(self, callback: Callable[[], None]) -> None:
        """Registra la función que se llamará automáticamente al terminar la canción actual."""
        self._on_track_end_callback = callback

    def _trigger_track_end(self) -> None:
        """Invoca el callback de fin de pista si está registrado."""
        if self._on_track_end_callback:
            try:
                self._on_track_end_callback()
            except Exception as e:
                print(f"[PLAYER] Error en callback on_track_end: {e}")

    @abstractmethod
    def play(self, track_info: Dict[str, Any]) -> bool:
        """Inicia la reproducción de una pista de audio."""
        pass

    @abstractmethod
    def pause(self) -> bool:
        """Pausa la reproducción actual."""
        pass

    @abstractmethod
    def resume(self) -> bool:
        """Reanuda la reproducción pausada."""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Detiene la reproducción por completo."""
        pass

    @abstractmethod
    def skip(self) -> bool:
        """Salta la pista actual disparando la transición a la siguiente."""
        pass

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Ajusta el volumen (de 0.0 a 1.0)."""
        pass

    @abstractmethod
    def get_volume(self) -> float:
        """Obtiene el volumen actual (de 0.0 a 1.0)."""
        pass

    @abstractmethod
    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Devuelve la información de la pista sonando actualmente, o None."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Devuelve el estado completo del reproductor:
        {
            "is_playing": bool,
            "is_paused": bool,
            "current_time": float (segundos),
            "duration": float (segundos),
            "volume": float (0.0 - 1.0),
            "current_track": dict or None
        }
        """
        pass
