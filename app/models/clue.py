"""线索模型。"""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import AuditMixin, IdMixin


class ClueModel(IdMixin, AuditMixin, Base):
    """统一线索实体。"""

    __tablename__ = "clue"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), nullable=False)
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
