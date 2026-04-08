"""会话根模型。"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin


class SessionModel(IdMixin, AuditMixin, Base):
    """一局游戏的根记录，承载全局状态与运行时文本内容。"""

    __tablename__ = "session"

    uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    start_time_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_time_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incident_time_minute: Mapped[int | None] = mapped_column(Integer)
    exposure_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_level: Mapped[str | None] = mapped_column(String(32), default="low")
    ending_type: Mapped[str | None] = mapped_column(String(64))
    accusation_state: Mapped[str | None] = mapped_column(String(64), default="idle")
    case_template_key: Mapped[str | None] = mapped_column(String(128))
    map_template_key: Mapped[str | None] = mapped_column(String(128))
    truth_template_key: Mapped[str | None] = mapped_column(String(128))
    truth_payload: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    story_markdown: Mapped[str | None] = mapped_column(Text)
    history_markdown: Mapped[str | None] = mapped_column(Text)
    truth_markdown: Mapped[str | None] = mapped_column(Text)
    latest_action_payload: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    ai_generation_log_entries: Mapped[list] = mapped_column(JSON_VARIANT, default=list, nullable=False)

    characters: Mapped[list["CharacterModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    player: Mapped["PlayerModel | None"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    npcs: Mapped[list["NpcModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    game_map: Mapped["MapModel | None"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    clues: Mapped[list["ClueModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["EventModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    dialogues: Mapped[list["DialogueModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
