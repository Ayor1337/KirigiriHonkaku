"""地图聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.map import LocationModel, MapModel


class MapRepository:
    """封装地图聚合读取。"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_by_session(self, session_id: str) -> MapModel | None:
        statement = (
            select(MapModel)
            .options(
                selectinload(MapModel.locations).selectinload(LocationModel.children),
                selectinload(MapModel.connections),
            )
            .where(MapModel.session_id == UUID(session_id))
        )
        return self.db_session.scalar(statement)
