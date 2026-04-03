"""规则模块协议定义。"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.models.character import NpcModel, PlayerModel
from app.models.clue import ClueModel
from app.models.dialogue import DialogueModel
from app.models.map import LocationModel, MapModel
from app.models.session import SessionModel
from app.schemas.action import ActionRequest


@dataclass
class ActionExecutionContext:
    """一次动作结算期间共享的聚合状态与临时结果。"""

    session: SessionModel
    player: PlayerModel
    npcs: list[NpcModel]
    game_map: MapModel
    clues: list[ClueModel]
    dialogues: list[DialogueModel]
    accepted: bool = True
    errors: list[str] = field(default_factory=list)
    previous_time_minute: int = 0
    resolved_target_location: LocationModel | None = None
    resolved_target_npc: NpcModel | None = None
    created_dialogue: DialogueModel | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def reject(self, error: str) -> None:
        """标记当前动作被拒绝，并记录原因。"""

        self.accepted = False
        self.errors.append(error)


class RuleModule(Protocol):
    """所有规则模块都需要实现的最小接口。"""

    name: str

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict[str, Any]:
        ...
