"""
Parser de Comandos de Chat y Motor de Búsqueda Difusa (Fuzzy Matching)
=====================================================================
Interpreta los mensajes entrantes de TikTok LIVE y busca coincidencias
en la biblioteca local de audio utilizando RapidFuzz.
"""

from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import process, fuzz


class CommandParser:
    def __init__(self, min_similarity_threshold: int = 50):
        # Umbral mínimo de similitud para aceptar una coincidencia de canción (0 a 100)
        self.min_similarity_threshold = min_similarity_threshold

    def parse_message(
        self,
        comment: str,
        user: str,
        nickname: str = "",
        indexed_tracks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analiza un comentario de chat. Si contiene un comando válido con '!',
        lo procesa y retorna un diccionario con el resultado.
        """
        raw_text = comment.strip()
        if not raw_text.startswith("!"):
            return None

        parts = raw_text.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        # Mapeo de comandos
        if cmd in ["!song", "!cancion", "!musica", "!play", "!pedir"]:
            if not args:
                return {
                    "command": "song",
                    "user": user,
                    "nickname": nickname,
                    "success": False,
                    "message": "Debes especificar el nombre de la canción. Ejemplo: !song Believer",
                    "track": None
                }
            
            matched_track, score = self.find_best_match(args, indexed_tracks or [])
            if matched_track and score >= self.min_similarity_threshold:
                return {
                    "command": "song",
                    "user": user,
                    "nickname": nickname,
                    "success": True,
                    "message": f"Encontrada: '{matched_track['title']}' ({score:.0f}% coincidencia)",
                    "track": matched_track,
                    "score": score,
                    "query": args
                }
            else:
                return {
                    "command": "song",
                    "user": user,
                    "nickname": nickname,
                    "success": False,
                    "message": f"No se encontró ninguna canción similar a '{args}' en la biblioteca local.",
                    "track": None,
                    "query": args
                }

        elif cmd in ["!skip", "!siguiente", "!next"]:
            return {
                "command": "skip",
                "user": user,
                "nickname": nickname,
                "args": args
            }

        elif cmd in ["!pause", "!pausa"]:
            return {
                "command": "pause",
                "user": user,
                "nickname": nickname
            }

        elif cmd in ["!resume", "!reanudar", "!unpause"]:
            return {
                "command": "resume",
                "user": user,
                "nickname": nickname
            }

        elif cmd in ["!clear", "!limpiar", "!vaciar"]:
            return {
                "command": "clear",
                "user": user,
                "nickname": nickname
            }

        elif cmd in ["!queue", "!cola", "!lista"]:
            return {
                "command": "queue",
                "user": user,
                "nickname": nickname
            }

        elif cmd in ["!current", "!actual", "!np", "!sonando"]:
            return {
                "command": "current",
                "user": user,
                "nickname": nickname
            }

        elif cmd in ["!help", "!ayuda", "!comandos"]:
            return {
                "command": "help",
                "user": user,
                "nickname": nickname,
                "message": "Comandos disponibles: !song <nombre>, !current, !queue. Moderadores: !skip, !pause, !resume, !clear"
            }

        return None

    def find_best_match(
        self,
        query: str,
        indexed_tracks: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Busca la pista de audio con mayor similitud con respecto al texto buscado.
        Utiliza token_set_ratio para ser tolerante al orden de palabras (ej. "Queen Bohemian" vs "Bohemian Rhapsody Queen").
        """
        if not indexed_tracks or not query:
            return None, 0.0

        choices = [t["search_text"] for t in indexed_tracks]
        result = process.extractOne(
            query.lower(),
            choices,
            scorer=fuzz.token_set_ratio
        )

        if result:
            match_str, score, index = result
            return indexed_tracks[index], float(score)

        return None, 0.0
