from __future__ import annotations

import json
from typing import Any

from x_claw.core.capability_manager import CapabilityManager
from x_claw.core.llm_provider import LLMProvider
from x_claw.core.memory_store import NoopMemoryStore
from x_claw.core.quota_manager import InMemoryQuotaManager, QuotaExceeded
from x_claw.core.session_store import InMemorySessionStore
from x_claw.core.task_router import TaskRouter
from x_claw.mcp.client_wrapper import MCPClientWrapper
from x_claw.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY
from x_claw.schemas import AgentResult, TaskType, UnifiedMessage


class XClawCore:
    def __init__(
        self,
        llm_provider: LLMProvider,
        mcp_client: MCPClientWrapper,
        session_store: InMemorySessionStore,
        memory_store: NoopMemoryStore,
        quota_manager: InMemoryQuotaManager,
        task_router: TaskRouter,
        max_iterations: int = 50,
        enable_tool_calls: bool = True,
    ) -> None:
        self.llm = llm_provider
        self.mcp = mcp_client
        self.sessions = session_store
        self.memory = memory_store
        self.quotas = quota_manager
        self.router = task_router
        self.max_iterations = max_iterations
        self.enable_tool_calls = enable_tool_calls
        self.capability_manager = CapabilityManager(self.llm.get_capabilities())

    async def process_message(self, msg: UnifiedMessage) -> AgentResult:
        task_type = self.router.classify(msg.content)

        try:
            await self.quotas.check_and_consume(msg.user_id, task_type)
        except QuotaExceeded as exc:
            return AgentResult(success=False, answer=str(exc), task_type=task_type, error="quota_exceeded")

        timer = REQUEST_LATENCY.labels(task_type=task_type.value).time()
        timer.__enter__()
        try:
            session_key = f"{msg.platform}:{msg.user_id}:{msg.chat_id}"
            session = await self.sessions.get_or_create(session_key, msg.user_id, msg.chat_id, msg.platform)
            memories = await self.memory.retrieve_long_term(msg.user_id, msg.content, top_k=5)
            agent_cfg = self.capability_manager.get_agent_config(task_type)

            tools: list[dict[str, Any]] = []
            if self.enable_tool_calls and agent_cfg.get("enable_tools", False):
                tools = await self.mcp.get_available_tools()

            messages = self._build_messages(session.history, msg.content, memories, agent_cfg, task_type)
            result = await self._agent_loop(
                messages=messages,
                tools=tools,
                task_type=task_type,
                max_iterations=min(int(agent_cfg["max_iterations"]), self.max_iterations),
                max_tool_calls=int(agent_cfg.get("max_tool_calls", 0)),
            )

            answer = result.answer
            if agent_cfg.get("fallback_notice"):
                answer = f"{agent_cfg['fallback_notice']}\n\n{answer}"
                result.answer = answer

            if result.success:
                await self.sessions.append_history(session_key, msg.content, answer)
                await self.memory.save_long_term(msg.user_id, msg.content, answer)
                REQUEST_COUNT.labels(platform=msg.platform, status="success", task_type=task_type.value).inc()
            else:
                REQUEST_COUNT.labels(platform=msg.platform, status="failure", task_type=task_type.value).inc()
            return result
        finally:
            timer.__exit__(None, None, None)
            await self.quotas.release(msg.user_id, task_type)

    def _build_messages(
        self,
        history: list[dict[str, Any]],
        user_content: str,
        memories: list[str],
        agent_cfg: dict[str, Any],
        task_type: TaskType,
    ) -> list[dict[str, Any]]:
        system_prompt = self._system_prompt(task_type, memories, agent_cfg)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_content})
        return messages

    def _system_prompt(self, task_type: TaskType, memories: list[str], agent_cfg: dict[str, Any]) -> str:
        base = [
            "你是 X-Claw 企业级智能助手。",
            f"当前任务类型: {task_type.value}",
            f"当前策略: {agent_cfg.get('strategy')}",
            "优先给出准确、可执行、结构化的回答。",
        ]
        if memories:
            base.append("以下是相关历史记忆（按相关性排序）：")
            base.extend([f"- {m}" for m in memories[:5]])
        if not agent_cfg.get("enable_tools", False):
            base.append("本次任务不允许使用工具，请直接回答。")
        else:
            base.append("如需使用工具，请优先少量关键调用，避免无意义重复搜索。")
        return "\n".join(base)

    async def _agent_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        task_type: TaskType,
        max_iterations: int,
        max_tool_calls: int,
    ) -> AgentResult:
        tool_call_count = 0
        for iteration in range(1, max_iterations + 1):
            response = await self.llm.chat_with_tools(
                messages=messages,
                tools=tools,
                max_tokens=2048 if task_type == TaskType.SIMPLE_QA else 4096,
                temperature=0.2,
            )

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []

            if not tool_calls:
                return AgentResult(
                    success=True,
                    answer=message.content or "",
                    task_type=task_type,
                    tool_calls=tool_call_count,
                    iterations=iteration,
                )

            if tool_call_count + len(tool_calls) > max_tool_calls:
                return AgentResult(
                    success=False,
                    answer="工具调用次数超过当前任务预算，请缩小问题范围后重试。",
                    task_type=task_type,
                    tool_calls=tool_call_count,
                    iterations=iteration,
                    error="tool_budget_exceeded",
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in tool_calls],
                }
            )

            for tool_call in tool_calls:
                tool_call_count += 1
                tool_name_full = tool_call.function.name
                try:
                    server_name, tool_name = tool_name_full.split("__", 1)
                except ValueError:
                    server_name, tool_name = "local", "ping"
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                tool_res = await self.mcp.call_tool(server_name, tool_name, args)
                tool_content = tool_res.content if tool_res.success else f"[TOOL_ERROR] {tool_res.error}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_content,
                    }
                )

        return AgentResult(
            success=False,
            answer="处理超时（达到最大迭代次数）",
            task_type=task_type,
            tool_calls=tool_call_count,
            iterations=max_iterations,
            error="max_iterations_reached",
        )

