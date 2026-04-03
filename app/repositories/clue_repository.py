"""线索聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.clue import ClueModel


class ClueRepository:
    """封装线索聚合读取。"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def list_by_session(self, session_id: str) -> list[ClueModel]:
        statement = (
            select(ClueModel)
            .options(
                joinedload(ClueModel.initial_location),
                joinedload(ClueModel.initial_holder_character),
                joinedload(ClueModel.current_location),
                joinedload(ClueModel.current_holder_character),
            )
            .where(ClueModel.session_id == UUID(session_id))
            .order_by(ClueModel.created_at)
        )
        return list(self.db_session.scalars(statement).unique())
