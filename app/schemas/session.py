"""会话相关 schema。"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    """创建最小会话所需的请求体。"""

    title: str
    case_template_key: str
    map_template_key: str
    truth_template_key: str


class SessionResponse(BaseModel):
    """会话接口返回结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uuid: str
    title: str
    status: str
    start_time_minute: int
    current_time_minute: int
    case_template_key: str | None = None
    map_template_key: str | None = None
    truth_template_key: str | None = None
    data_directories: dict[str, Any] = Field(default_factory=dict)


class SessionBootstrapResponse(BaseModel):
    """世界 bootstrap 接口返回结构。"""

    session_id: str
    status: str
    created_counts: dict[str, int] = Field(default_factory=dict)
    root_ids: dict[str, str] = Field(default_factory=dict)
