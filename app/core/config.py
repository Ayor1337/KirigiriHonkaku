"""应用配置定义。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """统一管理应用配置，并支持从环境变量加载。"""

    app_name: str = "Kirigiri Honkaku"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/kirigiri_honkaku"
    data_root: Path = Path("data")
    auto_create_schema: bool = False
    sql_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KIRIGIRI_",
        extra="ignore",
    )

    @property
    def resolved_data_root(self) -> Path:
        """返回运行时数据目录的绝对路径。"""

        return self.data_root.resolve()
