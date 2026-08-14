"""
Control de Permisos de Usuarios
===============================
Gestiona la lista blanca (allowlist) de streamers y moderadores
para restringir comandos administrativos (!skip, !clear, !pause, !resume),
con soporte para permitir el comando !skip a todos los usuarios o solo a moderadores.
"""

from typing import List, Optional


class PermissionManager:
    def __init__(
        self,
        streamer_id: str = "",
        moderators: Optional[List[str]] = None,
        skip_permission: str = "mods"
    ):
        self.streamer_id = self._normalize(streamer_id)
        self.moderators = set(self._normalize(m) for m in (moderators or []))
        self.skip_permission = "all" if "all" in str(skip_permission).lower() or "todo" in str(skip_permission).lower() else "mods"

    def _normalize(self, username: Optional[str]) -> str:
        if not username:
            return ""
        return username.strip().lstrip("@").lower()

    def set_skip_permission(self, mode: str) -> None:
        """Configura quién puede usar !skip: 'mods' o 'all'."""
        self.skip_permission = "all" if "all" in str(mode).lower() or "todo" in str(mode).lower() else "mods"

    def update_permissions(self, streamer_id: str, moderators: List[str]) -> None:
        """Actualiza dinámicamente las listas de permisos."""
        self.streamer_id = self._normalize(streamer_id)
        self.moderators = set(self._normalize(m) for m in moderators)

    def is_streamer(self, username: str) -> bool:
        """Verifica si el usuario es el streamer principal."""
        normalized = self._normalize(username)
        return bool(self.streamer_id and normalized == self.streamer_id)

    def is_moderator(self, username: str) -> bool:
        """Verifica si el usuario es streamer o está en la lista de moderadores."""
        normalized = self._normalize(username)
        if self.is_streamer(normalized):
            return True
        return normalized in self.moderators

    def can_skip(self, username: str) -> bool:
        """Determina si un usuario puede ejecutar !skip (según la configuración: solo mods o todos)."""
        if self.skip_permission == "all":
            return True
        return self.is_moderator(username)

    def can_clear(self, username: str) -> bool:
        """Determina si un usuario puede vaciar la cola (!clear)."""
        return self.is_moderator(username)

    def can_control_playback(self, username: str) -> bool:
        """Determina si un usuario puede pausar o reanudar."""
        return self.is_moderator(username)
