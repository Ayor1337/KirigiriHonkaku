"""会话根模型。"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import AuditMixin, IdMixin


class SessionModel(IdMixin, AuditMixin, Base):
    """一局游戏的根记录，承载全局状态与文本附件路径。"""

    __tablename__ = "session"

    uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    start_time_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_time_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incident_time_minute: Mapped[int | None] = mapped_column(Integer)
    exposure_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_level: Mapped[str | None] = mapped_column(String(32))
    ending_type: Mapped[str | None] = mapped_column(String(64))
    accusation_state: Mapped[str | None] = mapped_column(String(64))
    case_template_key: Mapped[str | None] = mapped_column(String(128))
    map_template_key: Mapped[str | None] = mapped_column(String(128))
    truth_template_key: Mapped[str | None] = mapped_column(String(128))
    story_file_path: Mapped[str | None] = mapped_column(Text)
    history_file_path: Mapped[str | None] = mapped_column(Text)
    truth_file_path: Mapped[str | None] = mapped_column(Text)

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
