"""对话聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.dialogue import DialogueModel, DialogueParticipantModel, UtteranceModel


class DialogueRepository:
    """封装对话聚合读取。"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def list_by_session(self, session_id: str) -> list[DialogueModel]:
        statement = (
            select(DialogueModel)
            .options(
                joinedload(DialogueModel.location),
                selectinload(DialogueModel.participants).joinedload(DialogueParticipantModel.character),
                selectinload(DialogueModel.utterances).joinedload(UtteranceModel.speaker_character),
            )
            .where(DialogueModel.session_id == UUID(session_id))
            .order_by(DialogueModel.start_minute, DialogueModel.created_at)
        )
        return list(self.db_session.scalars(statement).unique())
