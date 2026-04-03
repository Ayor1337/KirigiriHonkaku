"""地图检查规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class MapRule:
    """处理移动动作的最小位置变更。"""

    name = "map"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """在动作通过预校验后更新玩家位置。"""

        if not context.accepted or action.action_type != "move":
            return {"movement": None}

        origin = context.player.character.current_location
        target = context.resolved_target_location
        if origin is None or target is None:
            context.reject("Target location does not exist.")
            return {"movement": None}

        context.player.character.current_location = target
        return {
            "movement": {
                "from_location_key": origin.key,
                "to_location_key": target.key,
            }
        }
