"""地图体系模型。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin


class MapModel(IdMixin, AuditMixin, Base):
    """会话级地图根对象。"""

    __tablename__ = "map"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(255))


class LocationModel(IdMixin, AuditMixin, Base):
    """统一空间点模型。"""

    __tablename__ = "location"

    map_id: Mapped[str] = mapped_column(ForeignKey("map.id"), nullable=False)
    parent_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_type: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility_level: Mapped[str | None] = mapped_column(String(32))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)


class ConnectionModel(IdMixin, AuditMixin, Base):
    """地点之间的连接关系。"""

    __tablename__ = "connection"

    map_id: Mapped[str] = mapped_column(ForeignKey("map.id"), nullable=False)
    from_location_id: Mapped[str] = mapped_column(ForeignKey("location.id"), nullable=False)
    to_location_id: Mapped[str] = mapped_column(ForeignKey("location.id"), nullable=False)
    connection_type: Mapped[str | None] = mapped_column(String(64))
    access_rule: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_one_way: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dangerous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_window_rule: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)
