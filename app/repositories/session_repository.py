"""会话仓库实现。"""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import SessionModel


class SessionRepository:
    """封装 Session 聚合的数据库访问。"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create(self) -> SessionModel:
        """创建最小会话根记录。"""

        session = SessionModel(
            uuid=str(uuid4()),
            title=None,
            status="draft",
            start_time_minute=0,
            current_time_minute=0,
            exposure_value=0,
            exposure_level="low",
            accusation_state="idle",
            truth_payload={},
        )
        self.db_session.add(session)
        self.db_session.flush()
        return session

    def get(self, session_id: str) -> SessionModel | None:
        """按主键读取会话。"""

        return self.db_session.get(SessionModel, UUID(session_id))

    def get_by_uuid(self, session_uuid: str) -> SessionModel | None:
        """按外部 UUID 读取会话。"""

        statement = select(SessionModel).where(SessionModel.uuid == session_uuid)
        return self.db_session.scalar(statement)

    def list_all(self) -> list[SessionModel]:
        """读取全部会话，按创建时间倒序。"""

        statement = select(SessionModel).order_by(SessionModel.created_at.desc())
        return list(self.db_session.scalars(statement))
