"""地图检查规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class MapRule:
    """为后续地图可达性与路径规则预留骨架。"""

    name = "map"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """返回本次动作是否触发地图层检查。"""

        return {"map_checked": action.action_type == "move"}
