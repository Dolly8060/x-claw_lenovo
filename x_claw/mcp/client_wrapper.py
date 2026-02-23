from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Awaitable, Callable

import yaml

from x_claw.observability.metrics import TOOL_CALL_COUNT
from x_claw.schemas import ToolExecutionResult


ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(slots=True)
class ToolMeta:
    server_name: str
    tool_name: str
    timeout_sec: int = 30
    retries: int = 1
    enabled: bool = True
    fallback_server: str | None = None


class MCPClientWrapper:
    """
    骨架版 MCP 包装器。
    目标是先把超时/重试/降级/审计的接口定下来，再接入真实 MCP SDK。
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path) if config_path else None
        self.tools: dict[tuple[str, str], ToolMeta] = {}
        self.handlers: dict[tuple[str, str], ToolHandler] = {}
        self.server_health: dict[str, str] = {}

    def load_config(self) -> None:
        if not self.config_path or not self.config_path.exists():
            return
        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        for server_name, cfg in (raw.get("mcp_servers") or {}).items():
            enabled = bool(cfg.get("enabled", True))
            timeout_sec = int(cfg.get("timeout_sec", 30))
            retries = int(cfg.get("retries", 1))
            fallback = cfg.get("fallback")
            placeholder_name = "execute"
            self.tools[(server_name, placeholder_name)] = ToolMeta(
                server_name=server_name,
                tool_name=placeholder_name,
                timeout_sec=timeout_sec,
                retries=retries,
                enabled=enabled,
                fallback_server=fallback,
            )

    def register_local_handler(self, server_name: str, tool_name: str, handler: ToolHandler) -> None:
        key = (server_name, tool_name)
        self.handlers[key] = handler
        self.tools.setdefault(key, ToolMeta(server_name=server_name, tool_name=tool_name))

    async def initialize(self) -> None:
        self.load_config()
        # TODO: 接入真实 MCP SDK (stdio/sse/http) 会话初始化
        if ("local", "ping") not in self.handlers:
            self.register_local_handler("local", "ping", self._local_ping)
        self.server_health.setdefault("local", "healthy")

    async def get_available_tools(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for (server_name, tool_name), meta in self.tools.items():
            if not meta.enabled:
                continue
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"{server_name}__{tool_name}",
                        "description": f"Tool {tool_name} on MCP server {server_name}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string", "description": "Tool input payload"},
                                "raw": {"type": "object", "description": "Optional raw JSON payload"},
                            },
                        },
                    },
                }
            )
        return result

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        key = (server_name, tool_name)
        meta = self.tools.get(key)
        if meta is None:
            return ToolExecutionResult(success=False, content="", latency_ms=0, error=f"tool not found: {server_name}.{tool_name}")
        if not meta.enabled:
            return ToolExecutionResult(success=False, content="", latency_ms=0, error=f"tool disabled: {server_name}.{tool_name}")

        handler = self.handlers.get(key)
        if handler is None:
            return ToolExecutionResult(
                success=False,
                content="",
                latency_ms=0,
                error=(
                    f"no handler registered for {server_name}.{tool_name}; "
                    "plug real MCP SDK in x_claw/mcp/client_wrapper.py"
                ),
            )

        last_error: str | None = None
        for attempt in range(meta.retries + 1):
            started = perf_counter()
            try:
                text = await asyncio.wait_for(handler(arguments), timeout=meta.timeout_sec)
                latency_ms = int((perf_counter() - started) * 1000)
                TOOL_CALL_COUNT.labels(server_name=server_name, tool_name=tool_name, status="success").inc()
                return ToolExecutionResult(success=True, content=text, latency_ms=latency_ms)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                TOOL_CALL_COUNT.labels(server_name=server_name, tool_name=tool_name, status="failure").inc()
                if attempt >= meta.retries:
                    latency_ms = int((perf_counter() - started) * 1000)
                    return ToolExecutionResult(success=False, content="", latency_ms=latency_ms, error=last_error)
        return ToolExecutionResult(success=False, content="", latency_ms=0, error=last_error or "unknown error")

    async def ping(self, server_name: str) -> bool:
        if server_name == "local":
            res = await self.call_tool("local", "ping", {})
            return res.success
        return self.server_health.get(server_name) == "healthy"

    async def _local_ping(self, args: dict[str, Any]) -> str:
        return json.dumps({"ok": True, "echo": args}, ensure_ascii=False)

