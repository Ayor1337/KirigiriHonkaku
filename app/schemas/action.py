"""动作链路相关 schema。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


HARD_STATE_KEYS = {
    "current_time_minute",
    "player_location_id",
    "npc_location_id",
    "map_access",
    "clue_state",
    "clue_exists",
    "exposure_value",
    "ending_type",
    "accusation_state",
    "schedule_mode",
}


class ActionRequest(BaseModel):
    """统一动作输入。"""

    session_id: str
    action_type: Literal["move", "talk", "investigate", "accuse"]
    actor_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class SceneSnapshot(BaseModel):
    """引擎产出的结构化场景快照。"""

    session_id: str
    actor_id: str
    current_time_minute: int
    details: dict[str, Any] = Field(default_factory=dict)


class AiTask(BaseModel):
    """引擎分配给 AI Runtime 的任务描述。"""

    task_name: str
    context: dict[str, Any] = Field(default_factory=dict)


class SoftStatePatch(BaseModel):
    """AI Runtime 返回的受限软状态更新。"""

    allowed: bool = True
    updates: dict[str, Any] = Field(default_factory=dict)
    applied_updates: dict[str, Any] = Field(default_factory=dict)
    rejected_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def split_hard_state_updates(self) -> "SoftStatePatch":
        """剥离越权的硬状态字段，确保 AI 不直接改世界硬状态。"""

        rejected = [key for key in self.updates if key in HARD_STATE_KEYS]
        applied = {key: value for key, value in self.updates.items() if key not in HARD_STATE_KEYS}
        self.rejected_keys = rejected
        self.applied_updates = applied
        self.allowed = self.allowed and not rejected
        return self


class ActionResult(BaseModel):
    """统一动作输出。"""

    status: str
    action_type: str
    state_delta_summary: dict[str, Any]
    scene_snapshot: SceneSnapshot
    ai_tasks: list[AiTask] = Field(default_factory=list)
    soft_state_patch: SoftStatePatch = Field(default_factory=SoftStatePatch)
    storage_refs: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class SessionActionEnvelope(BaseModel):
    """为后续扩展预留的动作响应包装结构。"""

    model_config = ConfigDict(from_attributes=True)

    result: ActionResult
