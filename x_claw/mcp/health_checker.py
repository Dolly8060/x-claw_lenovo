from __future__ import annotations

import asyncio
import contextlib
import logging

from x_claw.mcp.client_wrapper import MCPClientWrapper


class MCPHealthChecker:
    def __init__(self, mcp_client: MCPClientWrapper, interval_sec: int = 60) -> None:
        self.mcp_client = mcp_client
        self.interval_sec = interval_sec
        self._task: asyncio.Task | None = None
        self._running = False
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="mcp-health-checker")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def check_once(self) -> None:
        server_names = {server for server, _tool in self.mcp_client.tools.keys()}
        for server_name in server_names:
            try:
                ok = await self.mcp_client.ping(server_name)
                self.mcp_client.server_health[server_name] = "healthy" if ok else "unhealthy"
            except Exception as exc:  # noqa: BLE001
                self.mcp_client.server_health[server_name] = "unhealthy"
                self.logger.warning("MCP health check failed for %s: %s", server_name, exc)

    async def _run(self) -> None:
        while self._running:
            await self.check_once()
            await asyncio.sleep(self.interval_sec)

