"""对话体系模型。"""

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin, utc_now


class DialogueModel(IdMixin, AuditMixin, Base):
    """一次完整会话。"""

    __tablename__ = "dialogue"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    dialogue_type: Mapped[str | None] = mapped_column(String(64))
    location_id: Mapped[str] = mapped_column(ForeignKey("location.id"), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int | None] = mapped_column(Integer)
    summary_file_path: Mapped[str | None] = mapped_column(Text)
    transcript_file_path: Mapped[str | None] = mapped_column(Text)
    tag_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)


class DialogueParticipantModel(IdMixin, Base):
    """对话参与者关系。"""

    __tablename__ = "dialogue_participant"

    dialogue_id: Mapped[str] = mapped_column(ForeignKey("dialogue.id"), nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), nullable=False)
    participant_role: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UtteranceModel(IdMixin, Base):
    """对话中的单条发言。"""

    __tablename__ = "utterance"
    __table_args__ = (UniqueConstraint("dialogue_id", "sequence_no", name="uq_utterance_dialogue_sequence"),)

    dialogue_id: Mapped[str] = mapped_column(ForeignKey("dialogue.id"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_character_id: Mapped[str] = mapped_column(ForeignKey("character.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tone_tag: Mapped[str | None] = mapped_column(String(64))
    utterance_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
