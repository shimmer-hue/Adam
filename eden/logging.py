from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .utils import now_utc


@dataclass(slots=True)
class LogEvent:
    ts_utc: str
    level: str
    event: str
    message: str
    payload: dict[str, Any]


class RuntimeLog:
    def __init__(self, path: Path, *, memory_limit: int = 400) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._memory: deque[LogEvent] = deque(maxlen=memory_limit)
        self._lock = threading.Lock()

    def emit(self, level: str, event: str, message: str, **payload: Any) -> LogEvent:
        item = LogEvent(
            ts_utc=now_utc(),
            level=level.upper(),
            event=event,
            message=message,
            payload=payload,
        )
        with self._lock:
            self._memory.append(item)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(item), ensure_ascii=True) + "\n")
        return item

    def recent(self, limit: int = 100) -> list[LogEvent]:
        with self._lock:
            items = list(self._memory)
        return items[-limit:]
