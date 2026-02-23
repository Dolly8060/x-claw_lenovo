from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Session:
    key: str
    user_id: str
    chat_id: str
    platform: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    history: list[dict[str, Any]] = field(default_factory=list)

