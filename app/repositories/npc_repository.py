"""NPC 聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.character import NpcModel, NpcScheduleModel, NpcStateModel


class NpcRepository:
    """封装 NPC 聚合读取。"""

    def __init__(self, db_session: Session):
        """绑定当前请求事务中的 SQLAlchemy Session。"""

        self.db_session = db_session

    def list_by_session(self, session_id: str) -> list[NpcModel]:
        """读取会话中的全部 NPC，并预加载状态和日程。"""

        statement = (
            select(NpcModel)
            .options(
                joinedload(NpcModel.character),
                joinedload(NpcModel.state).joinedload(NpcStateModel.current_location),
                joinedload(NpcModel.schedule).selectinload(NpcScheduleModel.entries),
            )
            .where(NpcModel.session_id == UUID(session_id))
            .order_by(NpcModel.created_at)
        )
        return list(self.db_session.scalars(statement).unique())
