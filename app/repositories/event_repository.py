"""事件聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.event import EventModel, EventParticipantModel


class EventRepository:
    """封装事件聚合读取。"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def list_by_session(self, session_id: str) -> list[EventModel]:
        statement = (
            select(EventModel)
            .options(
                joinedload(EventModel.location),
                selectinload(EventModel.participants).joinedload(EventParticipantModel.character),
            )
            .where(EventModel.session_id == UUID(session_id))
            .order_by(EventModel.start_minute, EventModel.created_at)
        )
        return list(self.db_session.scalars(statement).unique())
