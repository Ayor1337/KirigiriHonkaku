"""角色体系模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin, UpdatedAtMixin, utc_now


class CharacterModel(IdMixin, AuditMixin, Base):
    """玩家和 NPC 共用的角色外壳。"""

    __tablename__ = "character"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    public_identity: Mapped[str | None] = mapped_column(String(255))
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_participate_dialogue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_hold_clue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PlayerModel(IdMixin, AuditMixin, Base):
    """玩家主模型。"""

    __tablename__ = "player"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), unique=True, nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    template_name: Mapped[str | None] = mapped_column(String(255))
    trait_text: Mapped[str | None] = mapped_column(Text)
    background_text: Mapped[str | None] = mapped_column(Text)


class PlayerStateModel(IdMixin, UpdatedAtMixin, Base):
    """玩家动态状态。"""

    __tablename__ = "player_state"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    hp_state: Mapped[str | None] = mapped_column(String(32))
    injury_state: Mapped[str | None] = mapped_column(String(32))
    poison_state: Mapped[str | None] = mapped_column(String(32))
    exposure_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_level: Mapped[str | None] = mapped_column(String(32))
    status_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    temporary_effects: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    unlocked_access: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)


class PlayerInventoryModel(IdMixin, UpdatedAtMixin, Base):
    """玩家资源与持有物状态。"""

    __tablename__ = "player_inventory"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    money_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resource_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    held_item_refs: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    equipped_item_refs: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    credential_refs: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    weapon_refs: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    document_refs: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)
class PlayerKnowledgeModel(IdMixin, Base):
    """玩家知识池容器。"""

    __tablename__ = "player_knowledge"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeTopicModel(IdMixin, AuditMixin, Base):
    """知识主题分类。"""

    __tablename__ = "knowledge_topic"

    player_knowledge_id: Mapped[str] = mapped_column(ForeignKey("player_knowledge.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class KnowledgeEntryModel(IdMixin, AuditMixin, Base):
    """知识池中的单条知识记录。"""

    __tablename__ = "knowledge_entry"

    player_knowledge_id: Mapped[str] = mapped_column(ForeignKey("player_knowledge.id"), nullable=False)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_topic.id"))
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref_id: Mapped[str | None] = mapped_column(String(36))
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance_level: Mapped[str | None] = mapped_column(String(32))
    learned_at_minute: Mapped[int | None] = mapped_column(Integer)


class DetectiveBoardModel(IdMixin, UpdatedAtMixin, Base):
    """玩家唯一侦探板。"""

    __tablename__ = "detective_board"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    board_layout_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
class BoardItemModel(IdMixin, AuditMixin, Base):
    """侦探板中的卡片。"""

    __tablename__ = "board_item"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position_x: Mapped[float | None] = mapped_column()
    position_y: Mapped[float | None] = mapped_column()
    group_key: Mapped[str | None] = mapped_column(String(128))


class BoardLinkModel(IdMixin, AuditMixin, Base):
    """侦探板卡片之间的连接。"""

    __tablename__ = "board_link"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    from_item_id: Mapped[str] = mapped_column(ForeignKey("board_item.id"), nullable=False)
    to_item_id: Mapped[str] = mapped_column(ForeignKey("board_item.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    style_key: Mapped[str | None] = mapped_column(String(128))


class BoardNoteModel(IdMixin, AuditMixin, Base):
    """侦探板自由备注。"""

    __tablename__ = "board_note"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position_x: Mapped[float | None] = mapped_column()
    position_y: Mapped[float | None] = mapped_column()


class NpcModel(IdMixin, AuditMixin, Base):
    """NPC 主模型。"""

    __tablename__ = "npc"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    role_type: Mapped[str | None] = mapped_column(String(128))
    profile_file_path: Mapped[str | None] = mapped_column(Text)
    memory_file_path: Mapped[str | None] = mapped_column(Text)


class NpcStateModel(IdMixin, UpdatedAtMixin, Base):
    """NPC 当前状态。"""

    __tablename__ = "npc_state"

    npc_id: Mapped[str] = mapped_column(ForeignKey("npc.id"), unique=True, nullable=False)
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    attitude_to_player: Mapped[str | None] = mapped_column(String(32))
    alertness_level: Mapped[str | None] = mapped_column(String(32))
    emotion_tag: Mapped[str | None] = mapped_column(String(32))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_in_event: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_under_pressure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)


class NpcScheduleModel(IdMixin, UpdatedAtMixin, Base):
    """NPC 日程容器。"""

    __tablename__ = "npc_schedule"

    npc_id: Mapped[str] = mapped_column(ForeignKey("npc.id"), unique=True, nullable=False)
    schedule_mode: Mapped[str | None] = mapped_column(String(64))
class ScheduleEntryModel(IdMixin, AuditMixin, Base):
    """NPC 日程中的单个时间片。"""

    __tablename__ = "schedule_entry"

    schedule_id: Mapped[str] = mapped_column(ForeignKey("npc_schedule.id"), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    behavior_type: Mapped[str] = mapped_column(String(64), nullable=False)
    behavior_description: Mapped[str | None] = mapped_column(Text)
    target_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
