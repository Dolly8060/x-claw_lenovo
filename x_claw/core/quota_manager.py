from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from x_claw.schemas import TaskType


class QuotaExceeded(Exception):
    pass


class InMemoryQuotaManager:
    """首次部署骨架版；生产建议替换为 Redis 实现。"""

    def __init__(self) -> None:
        self.daily_limits = {
            TaskType.SIMPLE_QA: 100,
            TaskType.SEARCH_SUMMARY: 50,
            TaskType.LONG_DOC_ANALYSIS: 20,
            TaskType.DEEP_RESEARCH: 10,
        }
        self.concurrent_limits = {
            TaskType.SIMPLE_QA: 2,
            TaskType.SEARCH_SUMMARY: 2,
            TaskType.LONG_DOC_ANALYSIS: 1,
            TaskType.DEEP_RESEARCH: 1,
        }
        self._daily_usage: dict[tuple[str, str, str], int] = defaultdict(int)
        self._concurrent_usage: dict[tuple[str, str], int] = defaultdict(int)

    def _day(self) -> str:
        return datetime.utcnow().strftime("%Y%m%d")

    async def check_and_consume(self, user_id: str, task_type: TaskType) -> None:
        day_key = (user_id, task_type.value, self._day())
        conc_key = (user_id, task_type.value)
        if self._daily_usage[day_key] >= self.daily_limits[task_type]:
            raise QuotaExceeded(f"{task_type.value} 日配额已用完")
        if self._concurrent_usage[conc_key] >= self.concurrent_limits[task_type]:
            raise QuotaExceeded(f"{task_type.value} 并发配额已达上限")
        self._daily_usage[day_key] += 1
        self._concurrent_usage[conc_key] += 1

    async def release(self, user_id: str, task_type: TaskType) -> None:
        conc_key = (user_id, task_type.value)
        if self._concurrent_usage[conc_key] > 0:
            self._concurrent_usage[conc_key] -= 1

