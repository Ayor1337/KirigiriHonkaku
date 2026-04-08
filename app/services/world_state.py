"""世界状态读取服务。"""

from dataclasses import dataclass


@dataclass
class WorldStateSnapshot:
    """Step 2 阶段的完整世界聚合快照。"""

    session: object
    player: object | None
    npcs: list[object]
    game_map: object | None
    clues: list[object]
    events: list[object]
    dialogues: list[object]


class WorldStateService:
    """统一装配会话级世界聚合。"""

    def __init__(self, uow_factory):
        """注入工作单元工厂，供读取世界聚合时按需创建事务。"""

        self._uow_factory = uow_factory

    def get_world(self, session_id: str) -> WorldStateSnapshot:
        """按会话 ID 读取当前完整世界快照。"""

        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None:
                raise LookupError(session_id)
            return WorldStateSnapshot(
                session=session,
                player=uow.players.get_by_session(session_id),
                npcs=uow.npcs.list_by_session(session_id),
                game_map=uow.maps.get_by_session(session_id),
                clues=uow.clues.list_by_session(session_id),
                events=uow.events.list_by_session(session_id),
                dialogues=uow.dialogues.list_by_session(session_id),
            )
