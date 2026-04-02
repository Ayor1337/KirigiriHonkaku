"""指认与结局规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class AccusationRule:
    """处理正式指认动作的最小骨架。"""

    name = "accusation"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """在收到 accuse 动作时更新指认状态。"""

        if action.action_type == "accuse":
            session.accusation_state = "submitted"
        return {"accusation_state": session.accusation_state}
