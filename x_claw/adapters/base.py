from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from x_claw.schemas import UnifiedMessage


class PlatformAdapter(ABC):
    @abstractmethod
    async def parse_incoming(self, payload: dict[str, Any], headers: dict[str, str]) -> UnifiedMessage | None:
        raise NotImplementedError

    @abstractmethod
    async def format_outgoing(self, response_text: str, incoming_payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

