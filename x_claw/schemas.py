from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    SIMPLE_QA = "simple_qa"
    SEARCH_SUMMARY = "search_summary"
    DEEP_RESEARCH = "deep_research"
    LONG_DOC_ANALYSIS = "long_doc_analysis"


@dataclass(slots=True)
class UnifiedMessage:
    user_id: str
    chat_id: str
    platform: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolExecutionResult:
    success: bool
    content: str
    latency_ms: int
    error: str | None = None


@dataclass(slots=True)
class AgentResult:
    success: bool
    answer: str
    task_type: TaskType
    tool_calls: int = 0
    iterations: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

