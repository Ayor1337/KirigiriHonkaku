"""对话聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.dialogue import DialogueModel, DialogueParticipantModel, UtteranceModel


class DialogueRepository:
    """封装对话聚合读取。"""

    def __init__(self, db_session: Session):
        """绑定当前请求事务中的 SQLAlchemy Session。"""

        self.db_session = db_session

    def _base_statement(self):
        """构造对话聚合的基础查询，统一预加载常用关联。"""

        return (
            select(DialogueModel)
            .options(
                joinedload(DialogueModel.location),
                selectinload(DialogueModel.participants).joinedload(DialogueParticipantModel.character),
                selectinload(DialogueModel.utterances).joinedload(UtteranceModel.speaker_character),
            )
        )

    def list_by_session(self, session_id: str) -> list[DialogueModel]:
        """读取某个会话下的全部对话，并按时间正序返回。"""

        statement = (
            self._base_statement()
            .where(DialogueModel.session_id == UUID(session_id))
            .order_by(DialogueModel.start_minute, DialogueModel.created_at)
        )
        return list(self.db_session.scalars(statement).unique())

    def get_by_session_and_id(self, session_id: str, dialogue_id: str) -> DialogueModel | None:
        """按会话和对话 ID 读取单个对话聚合。"""

        statement = self._base_statement().where(
            DialogueModel.session_id == UUID(session_id),
            DialogueModel.id == UUID(dialogue_id),
        )
        return self.db_session.scalars(statement).unique().one_or_none()
