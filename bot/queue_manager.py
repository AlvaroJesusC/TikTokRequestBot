"""
Gestor de Cola de Solicitudes (FIFO)
===================================
Administra la lista de reproducción de solicitudes de canciones,
así como el historial de canciones ya reproducidas.
"""

from collections import deque
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List


class QueueManager:
    """Gestiona la cola de canciones FIFO en memoria y su historial."""

    def __init__(self, max_history: int = 50):
        self._queue: deque[Dict[str, Any]] = deque()
        self._history: deque[Dict[str, Any]] = deque(maxlen=max_history)

    def add(self, track: Dict[str, Any], requested_by: str, requested_by_nickname: str = "") -> Dict[str, Any]:
        """Añade una pista al final de la cola FIFO."""
        item_id = str(uuid.uuid4())[:8]
        now_str = datetime.now().strftime("%H:%M:%S")
        
        queue_item = {
            "id": item_id,
            "track": track,
            "requested_by": requested_by.strip().lstrip("@"),
            "requested_by_nickname": requested_by_nickname or requested_by,
            "requested_at": now_str
        }
        self._queue.append(queue_item)
        print(f"[QUEUE] '{track.get('title')}' añadida a la cola por @{requested_by}. Posición: {len(self._queue)}")
        return queue_item

    def pop(self) -> Optional[Dict[str, Any]]:
        """Extrae y devuelve el siguiente elemento de la cola FIFO."""
        if not self._queue:
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[Dict[str, Any]]:
        """Devuelve el siguiente elemento sin extraerlo de la cola."""
        if not self._queue:
            return None
        return self._queue[0]

    def remove_by_id(self, item_id: str) -> bool:
        """Elimina un elemento específico de la cola por su ID."""
        for item in list(self._queue):
            if item.get("id") == item_id:
                self._queue.remove(item)
                return True
        return False

    def clear(self) -> int:
        """Vacía la cola y devuelve el número de canciones eliminadas."""
        count = len(self._queue)
        self._queue.clear()
        print(f"[QUEUE] Cola vaciada. Se eliminaron {count} canciones.")
        return count

    def add_to_history(self, item: Dict[str, Any]) -> None:
        """Registra una pista finalizada en el historial."""
        history_item = item.copy()
        history_item["played_at"] = datetime.now().strftime("%H:%M:%S")
        self._history.appendleft(history_item)

    def get_queue(self) -> List[Dict[str, Any]]:
        """Retorna una lista con todas las pistas en espera."""
        return list(self._queue)

    def get_history(self) -> List[Dict[str, Any]]:
        """Retorna el historial de canciones reproducidas."""
        return list(self._history)

    def size(self) -> int:
        """Cantidad de pistas en cola."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Indica si la cola está vacía."""
        return len(self._queue) == 0
