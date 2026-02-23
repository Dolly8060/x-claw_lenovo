from __future__ import annotations

from typing import Any

from x_claw.adapters.base import PlatformAdapter
from x_claw.schemas import UnifiedMessage


class TeamsAdapter(PlatformAdapter):
    """骨架版 Teams 适配器，生产需接 Bot Framework SDK 与鉴权。"""

    async def parse_incoming(self, payload: dict[str, Any], headers: dict[str, str]) -> UnifiedMessage | None:
        if payload.get("type") != "message":
            return None
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        from_user = payload.get("from", {}) or {}
        conversation = payload.get("conversation", {}) or {}
        return UnifiedMessage(
            user_id=from_user.get("id", "unknown"),
            chat_id=conversation.get("id", "unknown"),
            platform="teams",
            content=text,
            metadata={"activity_id": payload.get("id")},
        )

    async def format_outgoing(self, response_text: str, incoming_payload: dict[str, Any]) -> dict[str, Any]:
        return {"type": "message", "text": response_text}

