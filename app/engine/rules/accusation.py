"""指认与结局规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class AccusationRule:
    """处理正式指认动作的最小骨架。"""

    name = "accusation"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """在收到 accuse 动作时更新指认状态。"""

        if context.accepted and action.action_type == "accuse":
            context.session.accusation_state = "submitted"
        return {"accusation_state": context.session.accusation_state}
