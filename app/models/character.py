"""角色体系模型。"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin, UpdatedAtMixin


class CharacterModel(IdMixin, AuditMixin, Base):
    """玩家和 NPC 共用的角色外壳。"""

    __tablename__ = "character"
    __table_args__ = (CheckConstraint("kind IN ('player', 'npc')", name="character_kind"),)

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    public_identity: Mapped[str | None] = mapped_column(String(255))
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_participate_dialogue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_hold_clue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="characters")
    current_location: Mapped["LocationModel | None"] = relationship(
        back_populates="resident_characters",
        foreign_keys=[current_location_id],
    )
    player: Mapped["PlayerModel | None"] = relationship(back_populates="character", uselist=False)
    npc: Mapped["NpcModel | None"] = relationship(back_populates="character", uselist=False)
    initial_clues: Mapped[list["ClueModel"]] = relationship(
        back_populates="initial_holder_character",
        foreign_keys="ClueModel.initial_holder_character_id",
    )
    held_clues: Mapped[list["ClueModel"]] = relationship(
        back_populates="current_holder_character",
        foreign_keys="ClueModel.current_holder_character_id",
    )
    event_participations: Mapped[list["EventParticipantModel"]] = relationship(back_populates="character")
    dialogue_participations: Mapped[list["DialogueParticipantModel"]] = relationship(back_populates="character")
    utterances: Mapped[list["UtteranceModel"]] = relationship(back_populates="speaker_character")


class PlayerModel(IdMixin, AuditMixin, Base):
    """玩家主模型。"""

    __tablename__ = "player"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), unique=True, nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    template_name: Mapped[str | None] = mapped_column(String(255))
    trait_text: Mapped[str | None] = mapped_column(Text)
    background_text: Mapped[str | None] = mapped_column(Text)

    session: Mapped["SessionModel"] = relationship(back_populates="player")
    character: Mapped["CharacterModel"] = relationship(back_populates="player")
    state: Mapped["PlayerStateModel | None"] = relationship(
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan",
    )
    inventory: Mapped["PlayerInventoryModel | None"] = relationship(
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan",
    )
    knowledge: Mapped["PlayerKnowledgeModel | None"] = relationship(
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan",
    )
    detective_board: Mapped["DetectiveBoardModel | None"] = relationship(
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan",
    )


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

    player: Mapped["PlayerModel"] = relationship(back_populates="state")


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

    player: Mapped["PlayerModel"] = relationship(back_populates="inventory")


class PlayerKnowledgeModel(IdMixin, Base):
    """玩家知识池容器。"""

    __tablename__ = "player_knowledge"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    player: Mapped["PlayerModel"] = relationship(back_populates="knowledge")
    topics: Mapped[list["KnowledgeTopicModel"]] = relationship(
        back_populates="player_knowledge",
        cascade="all, delete-orphan",
    )
    entries: Mapped[list["KnowledgeEntryModel"]] = relationship(
        back_populates="player_knowledge",
        cascade="all, delete-orphan",
    )


class KnowledgeTopicModel(IdMixin, AuditMixin, Base):
    """知识主题分类。"""

    __tablename__ = "knowledge_topic"

    player_knowledge_id: Mapped[str] = mapped_column(ForeignKey("player_knowledge.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    player_knowledge: Mapped["PlayerKnowledgeModel"] = relationship(back_populates="topics")
    entries: Mapped[list["KnowledgeEntryModel"]] = relationship(back_populates="topic")


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

    player_knowledge: Mapped["PlayerKnowledgeModel"] = relationship(back_populates="entries")
    topic: Mapped["KnowledgeTopicModel | None"] = relationship(back_populates="entries")


class DetectiveBoardModel(IdMixin, UpdatedAtMixin, Base):
    """玩家唯一侦探板。"""

    __tablename__ = "detective_board"

    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), unique=True, nullable=False)
    board_layout_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    player: Mapped["PlayerModel"] = relationship(back_populates="detective_board")
    items: Mapped[list["BoardItemModel"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
    )
    links: Mapped[list["BoardLinkModel"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list["BoardNoteModel"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
    )


class BoardItemModel(IdMixin, AuditMixin, Base):
    """侦探板中的卡片。"""

    __tablename__ = "board_item"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content: Mapped[str | None] = mapped_column(Text)
    position_x: Mapped[float | None] = mapped_column()
    position_y: Mapped[float | None] = mapped_column()
    group_key: Mapped[str | None] = mapped_column(String(128))

    board: Mapped["DetectiveBoardModel"] = relationship(back_populates="items")
    outgoing_links: Mapped[list["BoardLinkModel"]] = relationship(
        back_populates="from_item",
        foreign_keys="BoardLinkModel.from_item_id",
    )
    incoming_links: Mapped[list["BoardLinkModel"]] = relationship(
        back_populates="to_item",
        foreign_keys="BoardLinkModel.to_item_id",
    )


class BoardLinkModel(IdMixin, AuditMixin, Base):
    """侦探板卡片之间的连接。"""

    __tablename__ = "board_link"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    from_item_id: Mapped[str] = mapped_column(ForeignKey("board_item.id"), nullable=False)
    to_item_id: Mapped[str] = mapped_column(ForeignKey("board_item.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    style_key: Mapped[str | None] = mapped_column(String(128))

    board: Mapped["DetectiveBoardModel"] = relationship(back_populates="links")
    from_item: Mapped["BoardItemModel"] = relationship(
        back_populates="outgoing_links",
        foreign_keys=[from_item_id],
    )
    to_item: Mapped["BoardItemModel"] = relationship(
        back_populates="incoming_links",
        foreign_keys=[to_item_id],
    )


class BoardNoteModel(IdMixin, AuditMixin, Base):
    """侦探板自由备注。"""

    __tablename__ = "board_note"

    board_id: Mapped[str] = mapped_column(ForeignKey("detective_board.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position_x: Mapped[float | None] = mapped_column()
    position_y: Mapped[float | None] = mapped_column()

    board: Mapped["DetectiveBoardModel"] = relationship(back_populates="notes")


class NpcModel(IdMixin, AuditMixin, Base):
    """NPC 主模型。"""

    __tablename__ = "npc"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    role_type: Mapped[str | None] = mapped_column(String(128))
    profile_markdown: Mapped[str | None] = mapped_column(Text)
    memory_markdown: Mapped[str | None] = mapped_column(Text)

    session: Mapped["SessionModel"] = relationship(back_populates="npcs")
    character: Mapped["CharacterModel"] = relationship(back_populates="npc")
    state: Mapped["NpcStateModel | None"] = relationship(
        back_populates="npc",
        uselist=False,
        cascade="all, delete-orphan",
    )
    schedule: Mapped["NpcScheduleModel | None"] = relationship(
        back_populates="npc",
        uselist=False,
        cascade="all, delete-orphan",
    )


class NpcStateModel(IdMixin, UpdatedAtMixin, Base):
    """NPC 当前状态。"""

    __tablename__ = "npc_state"

    npc_id: Mapped[str] = mapped_column(ForeignKey("npc.id"), unique=True, nullable=False)
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    attitude_to_player: Mapped[str | None] = mapped_column(String(32))
    alertness_level: Mapped[str | None] = mapped_column(String(32))
    emotion_tag: Mapped[str | None] = mapped_column(String(32))
    has_met_player: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_in_event: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_under_pressure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)

    npc: Mapped["NpcModel"] = relationship(back_populates="state")
    current_location: Mapped["LocationModel | None"] = relationship(
        back_populates="npc_states",
        foreign_keys=[current_location_id],
    )


class NpcScheduleModel(IdMixin, UpdatedAtMixin, Base):
    """NPC 日程容器。"""

    __tablename__ = "npc_schedule"

    npc_id: Mapped[str] = mapped_column(ForeignKey("npc.id"), unique=True, nullable=False)
    schedule_mode: Mapped[str | None] = mapped_column(String(64))

    npc: Mapped["NpcModel"] = relationship(back_populates="schedule")
    entries: Mapped[list["ScheduleEntryModel"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


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

    schedule: Mapped["NpcScheduleModel"] = relationship(back_populates="entries")
    target_location: Mapped["LocationModel | None"] = relationship(
        back_populates="target_schedule_entries",
        foreign_keys=[target_location_id],
    )
