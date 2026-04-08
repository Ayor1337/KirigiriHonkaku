"""应用配置定义。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """统一管理应用配置，并支持从环境变量加载。"""

    app_name: str = "Kirigiri Honkaku"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:25432/kirigiri_honkaku"
    auto_create_schema: bool = False
    sql_echo: bool = False
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_timeout_seconds: float = 30.0
    openai_game_generation_timeout_seconds: float = 600.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KIRIGIRI_",
        extra="ignore",
    )
