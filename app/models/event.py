"""事件模型。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin


class EventModel(IdMixin, AuditMixin, Base):
    """世界中的特殊规则事件。"""

    __tablename__ = "event"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_id: Mapped[str] = mapped_column(ForeignKey("location.id"), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    event_state: Mapped[str | None] = mapped_column(String(64))
    is_public_event: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rule_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="events")
    location: Mapped["LocationModel"] = relationship(back_populates="events")
    participants: Mapped[list["EventParticipantModel"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class EventParticipantModel(IdMixin, AuditMixin, Base):
    """事件参与者关系。"""

    __tablename__ = "event_participant"

    event_id: Mapped[str] = mapped_column(ForeignKey("event.id"), nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), nullable=False)
    participant_role: Mapped[str | None] = mapped_column(String(64))
    attendance_state: Mapped[str | None] = mapped_column(String(64))

    event: Mapped["EventModel"] = relationship(back_populates="participants")
    character: Mapped["CharacterModel"] = relationship(back_populates="event_participations")
