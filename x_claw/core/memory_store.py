from __future__ import annotations


class NoopMemoryStore:
    """首次部署可先用空实现，后续替换为 Redis + ChromaDB 实现。"""

    async def retrieve_long_term(self, user_id: str, query: str, top_k: int = 5) -> list[str]:
        return []

    async def save_long_term(self, user_id: str, query: str, answer: str) -> None:
        return None

