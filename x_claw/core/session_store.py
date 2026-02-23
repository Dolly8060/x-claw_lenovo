from __future__ import annotations

from datetime import datetime

from x_claw.core.models import Session


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def get_or_create(self, key: str, user_id: str, chat_id: str, platform: str) -> Session:
        session = self._sessions.get(key)
        if session is None:
            session = Session(key=key, user_id=user_id, chat_id=chat_id, platform=platform)
            self._sessions[key] = session
        session.last_active = datetime.utcnow()
        return session

    async def append_history(self, key: str, user_content: str, assistant_content: str) -> None:
        session = self._sessions.get(key)
        if not session:
            return
        session.history.extend(
            [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ]
        )
        session.history = session.history[-20:]
        session.last_active = datetime.utcnow()

