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
ALLOWED_NPC_SOFT_STATE_KEYS = {"attitude_to_player", "alertness_level", "emotion_tag"}
ALLOWED_DIALOGUE_SOFT_STATE_KEYS = {"tag_flags"}


class ActionRequest(BaseModel):
    """统一动作输入。"""

    session_id: str
    action_type: Literal["move", "talk", "investigate", "gather", "accuse"]
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
    npc_updates: dict[str, dict[str, Any]] = Field(default_factory=dict)
    dialogue_updates: dict[str, Any] = Field(default_factory=dict)
    rejected_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def split_hard_state_updates(self) -> "SoftStatePatch":
        """剥离越权字段，确保 AI 不直接改世界硬状态。"""

        filtered_npc_updates: dict[str, dict[str, Any]] = {}
        rejected_keys: list[str] = []

        for npc_key, updates in self.npc_updates.items():
            allowed_updates: dict[str, Any] = {}
            for field_name, value in updates.items():
                full_key = f"{npc_key}.{field_name}"
                if field_name in HARD_STATE_KEYS or field_name not in ALLOWED_NPC_SOFT_STATE_KEYS:
                    rejected_keys.append(full_key)
                    continue
                allowed_updates[field_name] = value
            if allowed_updates:
                filtered_npc_updates[npc_key] = allowed_updates

        filtered_dialogue_updates: dict[str, Any] = {}
        for field_name, value in self.dialogue_updates.items():
            if field_name in HARD_STATE_KEYS or field_name not in ALLOWED_DIALOGUE_SOFT_STATE_KEYS:
                rejected_keys.append(f"dialogue.{field_name}")
                continue
            filtered_dialogue_updates[field_name] = value

        self.npc_updates = filtered_npc_updates
        self.dialogue_updates = filtered_dialogue_updates
        self.rejected_keys = rejected_keys
        self.allowed = self.allowed and not rejected_keys
        return self


class ActionResult(BaseModel):
    """统一动作输出。"""

    status: str
    action_type: str
    state_delta_summary: dict[str, Any]
    scene_snapshot: SceneSnapshot
    ai_tasks: list[AiTask] = Field(default_factory=list)
    soft_state_patch: SoftStatePatch = Field(default_factory=SoftStatePatch)
    narrative_text: str | None = None
    errors: list[str] = Field(default_factory=list)


class SessionActionEnvelope(BaseModel):
    """为后续扩展预留的动作响应包装结构。"""

    model_config = ConfigDict(from_attributes=True)

    result: ActionResult
