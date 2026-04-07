"""世界生成阶段的结构化输出契约。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GameGenerationPlan(BaseModel):
    """多轮 AGENT 第一阶段产出的高层游戏规划。"""

    model_config = ConfigDict(extra="forbid")

    title: str
    premise: str
    setting: str
    tone: str
    target_location_count: int = Field(ge=3, le=8)
    target_npc_count: int = Field(ge=2, le=6)
    target_clue_count: int = Field(ge=2, le=8)
    target_event_count: int = Field(ge=1, le=4)


class MapBlueprint(BaseModel):
    """地图根对象。"""

    model_config = ConfigDict(extra="forbid")

    display_name: str
    template_key: str | None = None


class LocationBlueprint(BaseModel):
    """地点定义。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    description: str | None = None
    location_type: str
    parent_key: str | None = None
    visibility_level: str | None = None
    is_hidden: bool = False
    status_flags: dict[str, Any] = Field(default_factory=dict)


class ConnectionBlueprint(BaseModel):
    """地点连接定义。"""

    model_config = ConfigDict(extra="forbid")

    from_location_key: str
    to_location_key: str
    connection_type: str | None = None
    access_rule: dict[str, Any] = Field(default_factory=dict)
    is_hidden: bool = False
    is_locked: bool = False
    is_one_way: bool = False
    is_dangerous: bool = False
    time_window_rule: dict[str, Any] = Field(default_factory=dict)


class PlayerBlueprint(BaseModel):
    """玩家初始状态定义。"""

    model_config = ConfigDict(extra="forbid")

    display_name: str
    public_identity: str | None = None
    template_key: str | None = None
    template_name: str | None = None
    trait_text: str | None = None
    background_text: str | None = None
    start_location_key: str
    unlocked_access: list[str] = Field(default_factory=list)
    status_flags: dict[str, Any] = Field(default_factory=dict)


class NpcScheduleEntryBlueprint(BaseModel):
    """NPC 日程单条目。"""

    model_config = ConfigDict(extra="forbid")

    start_minute: int
    end_minute: int
    behavior_type: str
    behavior_description: str | None = None
    target_location_key: str
    priority: int = 0


class NpcBlueprint(BaseModel):
    """NPC 定义。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    public_identity: str | None = None
    location_key: str
    role_type: str | None = None
    profile_markdown: str = ""
    memory_markdown: str = ""
    attitude_to_player: str | None = None
    alertness_level: str | None = None
    emotion_tag: str | None = None
    schedule_mode: str | None = None
    schedule_entries: list[NpcScheduleEntryBlueprint] = Field(default_factory=list)


class ClueBlueprint(BaseModel):
    """线索定义。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    description: str | None = None
    clue_type: str
    initial_location_key: str | None = None
    initial_holder_character_key: str | None = None
    current_location_key: str | None = None
    current_holder_character_key: str | None = None
    is_key_clue: bool = False
    is_movable: bool = True
    is_time_sensitive: bool = False
    clue_state: str = "hidden"
    discovery_rule: dict[str, Any] = Field(default_factory=dict)
    document_markdown: str = ""


class EventParticipantBlueprint(BaseModel):
    """事件参与者定义。"""

    model_config = ConfigDict(extra="forbid")

    character_key: str
    participant_role: str | None = None
    attendance_state: str | None = None


class EventBlueprint(BaseModel):
    """事件定义。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    event_type: str
    description: str | None = None
    location_key: str
    start_minute: int
    end_minute: int
    event_state: str = "scheduled"
    is_public_event: bool = False
    rule_flags: dict[str, Any] = Field(default_factory=dict)
    participants: list[EventParticipantBlueprint] = Field(default_factory=list)


class TruthBlueprint(BaseModel):
    """真相与指认真值定义。"""

    model_config = ConfigDict(extra="forbid")

    culprit_npc_key: str
    required_clue_keys: list[str] = Field(default_factory=list)
    supporting_clue_keys: list[str] = Field(default_factory=list)
    false_verdict_targets: list[str] = Field(default_factory=list)
    public_accusation_event_keys: list[str] = Field(default_factory=list)
    countermeasure_plan: dict[str, Any] = Field(default_factory=dict)
    private_encounter_rules: dict[str, Any] = Field(default_factory=dict)


class WorldBlueprint(BaseModel):
    """AGENT 最终产出的完整可玩世界蓝图。"""

    model_config = ConfigDict(extra="forbid")

    title: str
    map: MapBlueprint
    locations: list[LocationBlueprint]
    connections: list[ConnectionBlueprint]
    player: PlayerBlueprint
    npcs: list[NpcBlueprint]
    clues: list[ClueBlueprint]
    events: list[EventBlueprint]
    truth: TruthBlueprint
