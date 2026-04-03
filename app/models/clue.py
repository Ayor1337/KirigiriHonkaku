"""线索模型。"""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import AuditMixin, IdMixin


class ClueModel(IdMixin, AuditMixin, Base):
    """统一线索实体。"""

    __tablename__ = "clue"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN initial_location_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN initial_holder_character_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="clue_initial_owner_xor",
        ),
        CheckConstraint(
            "(CASE WHEN current_location_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN current_holder_character_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="clue_current_owner_xor",
        ),
        UniqueConstraint("session_id", "key", name="uq_clue_session_key"),
    )

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    clue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    initial_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    initial_holder_character_id: Mapped[str | None] = mapped_column(ForeignKey("character.id"))
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    current_holder_character_id: Mapped[str | None] = mapped_column(ForeignKey("character.id"))
    is_key_clue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_movable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_time_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clue_state: Mapped[str | None] = mapped_column(String(64))
    document_file_path: Mapped[str | None] = mapped_column(Text)

    session: Mapped["SessionModel"] = relationship(back_populates="clues")
    initial_location: Mapped["LocationModel | None"] = relationship(
        back_populates="initial_clues",
        foreign_keys=[initial_location_id],
    )
    initial_holder_character: Mapped["CharacterModel | None"] = relationship(
        back_populates="initial_clues",
        foreign_keys=[initial_holder_character_id],
    )
    current_location: Mapped["LocationModel | None"] = relationship(
        back_populates="current_clues",
        foreign_keys=[current_location_id],
    )
    current_holder_character: Mapped["CharacterModel | None"] = relationship(
        back_populates="held_clues",
        foreign_keys=[current_holder_character_id],
    )
