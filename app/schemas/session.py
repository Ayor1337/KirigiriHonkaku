"""会话相关 schema。"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionSummaryResponse(BaseModel):
    """会话列表项返回结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uuid: str
    title: str | None = None
    status: str
    start_time_minute: int
    current_time_minute: int


class SessionStateResponse(BaseModel):
    """会话状态详情返回结构。"""

    exposure_value: int = 0
    exposure_level: str | None = None


class SessionPlayerResponse(BaseModel):
    """会话详情里的玩家资料。"""

    id: UUID
    character_id: UUID
    display_name: str
    public_identity: str | None = None
    template_key: str | None = None
    template_name: str | None = None
    trait_text: str | None = None
    background_text: str | None = None
    current_location_id: UUID | None = None
    current_location_name: str | None = None
    exposure_value: int = 0
    exposure_level: str | None = None


class SessionNpcResponse(BaseModel):
    """会话里的 NPC 简要资料。"""

    id: UUID
    character_id: UUID
    template_key: str | None = None
    display_name: str
    public_identity: str | None = None
    current_location_id: UUID | None = None
    current_location_name: str | None = None
    has_met_player: bool = False


class SessionDialogueUtteranceResponse(BaseModel):
    """聊天详情中的单条发言。"""

    sequence_no: int
    speaker_role: str | None = None
    speaker_name: str
    content: str
    tone_tag: str | None = None
    utterance_flags: dict[str, Any] = Field(default_factory=dict)


class SessionDialogueSummaryResponse(BaseModel):
    """聊天会话列表项。"""

    dialogue_id: UUID
    target_npc_key: str | None = None
    target_npc_name: str | None = None
    location_id: UUID | None = None
    location_key: str | None = None
    location_name: str | None = None
    start_minute: int
    end_minute: int | None = None
    utterance_count: int = 0
    last_utterance_preview: str | None = None


class SessionDialogueDetailResponse(SessionDialogueSummaryResponse):
    """单个聊天会话详情。"""

    tag_flags: dict[str, Any] = Field(default_factory=dict)
    utterances: list[SessionDialogueUtteranceResponse] = Field(default_factory=list)


class SessionMapLocationResponse(BaseModel):
    """会话详情里的地点资料。"""

    id: UUID
    key: str
    parent_location_id: UUID | None = None
    name: str
    description: str | None = None
    location_type: str
    visibility_level: str | None = None
    is_hidden: bool = False
    status_flags: dict[str, Any] = Field(default_factory=dict)


class SessionMapConnectionResponse(BaseModel):
    """会话详情里的地点连接资料。"""

    id: UUID
    from_location_id: UUID
    to_location_id: UUID
    connection_type: str | None = None
    access_rule: dict[str, Any] = Field(default_factory=dict)
    is_hidden: bool = False
    is_locked: bool = False
    is_one_way: bool = False
    is_dangerous: bool = False
    time_window_rule: dict[str, Any] = Field(default_factory=dict)


class SessionMapResponse(BaseModel):
    """会话详情里的地图资料。"""

    id: UUID
    template_key: str | None = None
    display_name: str | None = None
    locations: list[SessionMapLocationResponse] = Field(default_factory=list)
    connections: list[SessionMapConnectionResponse] = Field(default_factory=list)


class SessionResponse(SessionSummaryResponse):
    """会话基础详情接口返回结构。"""

    root_ids: dict[str, str] = Field(default_factory=dict)


class SessionBootstrapResponse(BaseModel):
    """世界 bootstrap 接口返回结构。"""

    session_id: str
    status: str
    created_counts: dict[str, int] = Field(default_factory=dict)
    root_ids: dict[str, str] = Field(default_factory=dict)


class SessionBootstrapStageEvent(BaseModel):
    """流式世界生成阶段事件。"""

    placeholder: str
    session_id: str | None = None
    attempt: int | None = None
    max_attempts: int | None = None


class SessionBootstrapErrorEvent(BaseModel):
    """流式世界生成错误事件。"""

    code: str
    message: str
    session_id: str | None = None
    failed_placeholder: str | None = None
