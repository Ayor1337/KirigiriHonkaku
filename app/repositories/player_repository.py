"""玩家聚合仓储。"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.character import CharacterModel, DetectiveBoardModel, PlayerKnowledgeModel, PlayerModel


class PlayerRepository:
    """封装玩家聚合读取。"""

    def __init__(self, db_session: Session):
        """绑定当前请求事务中的 SQLAlchemy Session。"""

        self.db_session = db_session

    def get_by_session(self, session_id: str) -> PlayerModel | None:
        """读取会话中的玩家聚合及其常用关联状态。"""

        statement = (
            select(PlayerModel)
            .options(
                joinedload(PlayerModel.character).joinedload(CharacterModel.current_location),
                joinedload(PlayerModel.state),
                joinedload(PlayerModel.inventory),
                joinedload(PlayerModel.knowledge).selectinload(PlayerKnowledgeModel.topics),
                joinedload(PlayerModel.knowledge).selectinload(PlayerKnowledgeModel.entries),
                joinedload(PlayerModel.detective_board).selectinload(DetectiveBoardModel.items),
                joinedload(PlayerModel.detective_board).selectinload(DetectiveBoardModel.links),
                joinedload(PlayerModel.detective_board).selectinload(DetectiveBoardModel.notes),
            )
            .where(PlayerModel.session_id == UUID(session_id))
        )
        return self.db_session.scalar(statement)

    def get_id_by_session(self, session_id: str) -> str | None:
        """按会话读取玩家根 ID。"""

        statement = select(PlayerModel.id).where(PlayerModel.session_id == UUID(session_id))
        player_id = self.db_session.scalar(statement)
        return str(player_id) if player_id is not None else None
