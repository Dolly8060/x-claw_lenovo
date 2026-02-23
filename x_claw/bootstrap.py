from __future__ import annotations

from dataclasses import dataclass

from x_claw.adapters.feishu_adapter import FeishuAdapter
from x_claw.adapters.teams_adapter import TeamsAdapter
from x_claw.core.engine import XClawCore
from x_claw.core.llm_provider import GenericOpenAIProvider, MiroThinkerProvider
from x_claw.core.memory_store import NoopMemoryStore
from x_claw.core.quota_manager import InMemoryQuotaManager
from x_claw.core.session_store import InMemorySessionStore
from x_claw.core.task_router import TaskRouter
from x_claw.mcp.client_wrapper import MCPClientWrapper
from x_claw.mcp.health_checker import MCPHealthChecker
from x_claw.settings import Settings


@dataclass(slots=True)
class AppContainer:
    core: XClawCore
    feishu_adapter: FeishuAdapter
    teams_adapter: TeamsAdapter
    mcp_client: MCPClientWrapper
    mcp_health_checker: MCPHealthChecker


async def build_container(settings: Settings) -> AppContainer:
    if settings.llm_provider.lower() == "mirothinker":
        llm_provider = MiroThinkerProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model_name=settings.llm_model,
            timeout_sec=settings.request_timeout_sec,
        )
    else:
        llm_provider = GenericOpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model_name=settings.llm_model,
        )

    mcp_client = MCPClientWrapper(config_path="config/mcp_servers.yaml")
    await mcp_client.initialize()
    health_checker = MCPHealthChecker(mcp_client)

    core = XClawCore(
        llm_provider=llm_provider,
        mcp_client=mcp_client,
        session_store=InMemorySessionStore(),
        memory_store=NoopMemoryStore(),
        quota_manager=InMemoryQuotaManager(),
        task_router=TaskRouter(),
        max_iterations=settings.max_agent_iterations,
        enable_tool_calls=settings.enable_tool_calls,
    )

    return AppContainer(
        core=core,
        feishu_adapter=FeishuAdapter(),
        teams_adapter=TeamsAdapter(),
        mcp_client=mcp_client,
        mcp_health_checker=health_checker,
    )

