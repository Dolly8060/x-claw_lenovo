from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from x_claw.bootstrap import AppContainer, build_container
from x_claw.observability.logging_utils import get_logger, setup_logging
from x_claw.observability.metrics import metrics_response
from x_claw.schemas import UnifiedMessage
from x_claw.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    container = await build_container(settings)
    app.state.container = container
    await container.mcp_health_checker.check_once()
    yield


app = FastAPI(title="X-Claw V2 Skeleton", version="0.1.0", lifespan=lifespan)


def _container(request: Request) -> AppContainer:
    return request.app.state.container


async def _handle_unified_message(container: AppContainer, msg: UnifiedMessage, trace_id: str) -> dict[str, Any]:
    logger = get_logger("x_claw.main", trace_id=trace_id)
    if not msg.content.strip():
        raise HTTPException(status_code=400, detail="empty message")
    logger.info("incoming message platform=%s user=%s", msg.platform, msg.user_id)
    result = await container.core.process_message(msg)
    logger.info(
        "processed platform=%s success=%s task_type=%s tool_calls=%s iterations=%s",
        msg.platform,
        result.success,
        result.task_type.value,
        result.tool_calls,
        result.iterations,
    )
    return {
        "success": result.success,
        "answer": result.answer,
        "task_type": result.task_type.value,
        "tool_calls": result.tool_calls,
        "iterations": result.iterations,
        "error": result.error,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready(request: Request) -> dict[str, Any]:
    container = _container(request)
    return {
        "status": "ready",
        "mcp_servers": container.mcp_client.server_health,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.post("/debug/message")
async def debug_message(request: Request):
    payload = await request.json()
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    msg = UnifiedMessage(
        user_id=payload.get("user_id", "debug-user"),
        chat_id=payload.get("chat_id", "debug-chat"),
        platform=payload.get("platform", "debug"),
        content=payload.get("content", ""),
        metadata=payload.get("metadata", {}),
    )
    return await _handle_unified_message(_container(request), msg, trace_id)


@app.post("/webhook/feishu")
async def webhook_feishu(request: Request):
    payload = await request.json()
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    container = _container(request)
    msg = await container.feishu_adapter.parse_incoming(payload, dict(request.headers))
    if msg is None:
        return JSONResponse({"status": "ignored"})
    result = await _handle_unified_message(container, msg, trace_id)
    return JSONResponse({"status": "ok", "result": result})


@app.post("/webhook/teams")
async def webhook_teams(request: Request):
    payload = await request.json()
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    container = _container(request)
    msg = await container.teams_adapter.parse_incoming(payload, dict(request.headers))
    if msg is None:
        return JSONResponse({"status": "ignored"})
    result = await _handle_unified_message(container, msg, trace_id)
    return JSONResponse({"status": "ok", "result": result})


def run() -> None:
    import uvicorn

    uvicorn.run("x_claw.main:app", host=settings.host, port=settings.port, reload=False)

