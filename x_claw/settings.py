from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    env: str = Field(default="dev", alias="XCLAW_ENV")
    host: str = Field(default="0.0.0.0", alias="XCLAW_HOST")
    port: int = Field(default=8080, alias="XCLAW_PORT")
    log_level: str = Field(default="INFO", alias="XCLAW_LOG_LEVEL")

    llm_provider: str = Field(default="mirothinker", alias="XCLAW_LLM_PROVIDER")
    llm_base_url: str = Field(default="http://localhost:8000/v1", alias="XCLAW_LLM_BASE_URL")
    llm_api_key: str = Field(default="dummy", alias="XCLAW_LLM_API_KEY")
    llm_model: str = Field(default="mirothinker-30b", alias="XCLAW_LLM_MODEL")
    request_timeout_sec: int = Field(default=300, alias="XCLAW_REQUEST_TIMEOUT_SEC")

    max_agent_iterations: int = Field(default=50, alias="XCLAW_MAX_AGENT_ITERATIONS")
    enable_tool_calls: bool = Field(default=True, alias="XCLAW_ENABLE_TOOL_CALLS")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="XCLAW_REDIS_URL")
    chroma_path: str = Field(default="./data/chroma", alias="XCLAW_CHROMA_PATH")

    feishu_encrypt_key: str = Field(default="", alias="XCLAW_FEISHU_ENCRYPT_KEY")
    feishu_verification_token: str = Field(default="", alias="XCLAW_FEISHU_VERIFICATION_TOKEN")
    teams_app_id: str = Field(default="", alias="XCLAW_TEAMS_APP_ID")
    teams_app_password: str = Field(default="", alias="XCLAW_TEAMS_APP_PASSWORD")


settings = Settings()

