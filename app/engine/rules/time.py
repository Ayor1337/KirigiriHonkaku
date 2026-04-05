"""时间推进规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class TimeRule:
    """处理动作带来的时间推进。"""

    name = "time"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """只在动作被接受时推进主循环时间。"""

        advanced = False
        if context.accepted and action.action_type in {"move", "investigate", "talk", "gather", "accuse"}:
            context.session.current_time_minute += 5
            advanced = True
        return {
            "advanced": advanced,
            "current_time_minute": context.session.current_time_minute,
        }
