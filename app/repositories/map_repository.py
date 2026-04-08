"""地图聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.map import LocationModel, MapModel


class MapRepository:
    """封装地图聚合读取。"""

    def __init__(self, db_session: Session):
        """绑定当前请求事务中的 SQLAlchemy Session。"""

        self.db_session = db_session

    def get_by_session(self, session_id: str) -> MapModel | None:
        """读取某个会话的地图根对象及其关联地点、连接。"""

        statement = (
            select(MapModel)
            .options(
                selectinload(MapModel.locations).selectinload(LocationModel.children),
                selectinload(MapModel.connections),
            )
            .where(MapModel.session_id == UUID(session_id))
        )
        return self.db_session.scalar(statement)

    def get_id_by_session(self, session_id: str) -> str | None:
        """按会话读取地图根 ID。"""

        statement = select(MapModel.id).where(MapModel.session_id == UUID(session_id))
        map_id = self.db_session.scalar(statement)
        return str(map_id) if map_id is not None else None
