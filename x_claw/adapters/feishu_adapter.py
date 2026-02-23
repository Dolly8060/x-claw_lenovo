from __future__ import annotations

import json
from typing import Any

from x_claw.adapters.base import PlatformAdapter
from x_claw.schemas import UnifiedMessage


class FeishuAdapter(PlatformAdapter):
    """
    骨架版飞书适配器。
    生产环境需补充：签名校验、解密、幂等去重、SDK 回发消息。
    """

    async def parse_incoming(self, payload: dict[str, Any], headers: dict[str, str]) -> UnifiedMessage | None:
        if "challenge" in payload:
            return None
        if payload.get("header", {}).get("event_type") != "im.message.receive_v1":
            return None

        event = payload.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        if message.get("message_type") != "text":
            return None

        try:
            content = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            content = {}

        return UnifiedMessage(
            user_id=sender.get("sender_id", {}).get("open_id", "unknown"),
            chat_id=message.get("chat_id", "unknown"),
            platform="feishu",
            content=(content.get("text") or "").strip(),
            metadata={
                "message_id": message.get("message_id"),
                "chat_type": message.get("chat_type"),
            },
        )

    async def format_outgoing(self, response_text: str, incoming_payload: dict[str, Any]) -> dict[str, Any]:
        return {"msg_type": "text", "content": {"text": response_text}}

