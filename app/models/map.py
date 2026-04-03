"""地图体系模型。"""

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT
from app.models.common import AuditMixin, IdMixin


class MapModel(IdMixin, AuditMixin, Base):
    """会话级地图根对象。"""

    __tablename__ = "map"

    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), unique=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(255))

    session: Mapped["SessionModel"] = relationship(back_populates="game_map")
    locations: Mapped[list["LocationModel"]] = relationship(
        back_populates="map",
        cascade="all, delete-orphan",
    )
    connections: Mapped[list["ConnectionModel"]] = relationship(
        back_populates="map",
        cascade="all, delete-orphan",
    )


class LocationModel(IdMixin, AuditMixin, Base):
    """统一空间点模型。"""

    __tablename__ = "location"
    __table_args__ = (UniqueConstraint("map_id", "key", name="uq_location_map_key"),)

    map_id: Mapped[str] = mapped_column(ForeignKey("map.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_location_id: Mapped[str | None] = mapped_column(ForeignKey("location.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_type: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility_level: Mapped[str | None] = mapped_column(String(32))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_flags: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict, nullable=False)

    map: Mapped["MapModel"] = relationship(back_populates="locations")
    parent: Mapped["LocationModel | None"] = relationship(
        remote_side="LocationModel.id",
        back_populates="children",
    )
    children: Mapped[list["LocationModel"]] = relationship(back_populates="parent")
    resident_characters: Mapped[list["CharacterModel"]] = relationship(
        back_populates="current_location",
        foreign_keys="CharacterModel.current_location_id",
    )
    npc_states: Mapped[list["NpcStateModel"]] = relationship(
        back_populates="current_location",
        foreign_keys="NpcStateModel.current_location_id",
    )
    target_schedule_entries: Mapped[list["ScheduleEntryModel"]] = relationship(
        back_populates="target_location",
        foreign_keys="ScheduleEntryModel.target_location_id",
    )
    initial_clues: Mapped[list["ClueModel"]] = relationship(
        back_populates="initial_location",
        foreign_keys="ClueModel.initial_location_id",
    )
    current_clues: Mapped[list["ClueModel"]] = relationship(
        back_populates="current_location",
        foreign_keys="ClueModel.current_location_id",
    )
    events: Mapped[list["EventModel"]] = relationship(back_populates="location")
    dialogues: Mapped[list["DialogueModel"]] = relationship(back_populates="location")
    outgoing_connections: Mapped[list["ConnectionModel"]] = relationship(
        back_populates="from_location",
        foreign_keys="ConnectionModel.from_location_id",
    )
    incoming_connections: Mapped[list["ConnectionModel"]] = relationship(
        back_populates="to_location",
        foreign_keys="ConnectionModel.to_location_id",
    )


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

    map: Mapped["MapModel"] = relationship(back_populates="connections")
    from_location: Mapped["LocationModel"] = relationship(
        back_populates="outgoing_connections",
        foreign_keys=[from_location_id],
    )
    to_location: Mapped["LocationModel"] = relationship(
        back_populates="incoming_connections",
        foreign_keys=[to_location_id],
    )
