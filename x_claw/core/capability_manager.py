from __future__ import annotations

from x_claw.core.llm_provider import ModelCapabilities
from x_claw.schemas import TaskType


class CapabilityManager:
    def __init__(self, capabilities: ModelCapabilities) -> None:
        self.capabilities = capabilities

    def get_agent_config(self, task_type: TaskType) -> dict:
        if task_type == TaskType.SIMPLE_QA:
            return {
                "strategy": "direct_answer",
                "max_iterations": 4,
                "enable_tools": False,
                "max_tool_calls": 0,
            }
        if task_type == TaskType.SEARCH_SUMMARY:
            return {
                "strategy": "search_summary",
                "max_iterations": 12,
                "enable_tools": self.capabilities.tool_calling_supported,
                "max_tool_calls": min(20, self.capabilities.max_tool_calls_hint),
            }
        if task_type == TaskType.LONG_DOC_ANALYSIS:
            return {
                "strategy": "long_doc_analysis",
                "max_iterations": 20,
                "enable_tools": self.capabilities.tool_calling_supported,
                "max_tool_calls": min(50, self.capabilities.max_tool_calls_hint),
            }
        if not self.capabilities.deep_research_supported:
            return {
                "strategy": "degraded_search_summary",
                "max_iterations": 10,
                "enable_tools": self.capabilities.tool_calling_supported,
                "max_tool_calls": min(20, self.capabilities.max_tool_calls_hint),
                "fallback_notice": "当前模型不支持深度研究模式，已降级为搜索总结模式。",
            }
        return {
            "strategy": "deep_research",
            "max_iterations": 50,
            "enable_tools": self.capabilities.tool_calling_supported,
            "max_tool_calls": min(200, self.capabilities.max_tool_calls_hint),
        }

