from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI


@dataclass(slots=True)
class ModelCapabilities:
    provider_name: str
    model_name: str
    max_context_length: int
    max_tool_calls_hint: int
    tool_calling_supported: bool
    deep_research_supported: bool


class LLMProvider(ABC):
    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str | None = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> Any:
        raise NotImplementedError


class MiroThinkerProvider(LLMProvider):
    """MiroThinker 30B via SGLang OpenAI-compatible endpoint."""

    def __init__(self, base_url: str, api_key: str, model_name: str, timeout_sec: int = 300) -> None:
        self.model_name = model_name
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout_sec)

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider_name="mirothinker",
            model_name=self.model_name,
            max_context_length=256_000,
            max_tool_calls_hint=600,
            tool_calling_supported=True,
            deep_research_supported=True,
        )

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str | None = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        return await self.client.chat.completions.create(**kwargs)


class GenericOpenAIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model_name: str) -> None:
        self.model_name = model_name
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider_name="generic_openai",
            model_name=self.model_name,
            max_context_length=128_000,
            max_tool_calls_hint=50,
            tool_calling_supported=True,
            deep_research_supported=False,
        )

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str | None = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        return await self.client.chat.completions.create(**kwargs)

