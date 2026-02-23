from __future__ import annotations

from x_claw.schemas import TaskType


class TaskRouter:
    """先用简单规则，后续再接分类模型或策略服务。"""

    def classify(self, content: str) -> TaskType:
        text = content.lower()
        if any(k in text for k in ["深度调研", "深入分析", "竞品", "研究", "research"]):
            return TaskType.DEEP_RESEARCH
        if any(k in text for k in ["文档", "pdf", "长文", "合同"]):
            return TaskType.LONG_DOC_ANALYSIS
        if any(k in text for k in ["搜索", "查一下", "查找", "搜索并总结"]):
            return TaskType.SEARCH_SUMMARY
        return TaskType.SIMPLE_QA

