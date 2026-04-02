"""时间推进规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class TimeRule:
    """处理动作带来的时间推进。"""

    name = "time"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """对可推进时间的动作增加会话时间。"""

        if action.action_type in {"move", "investigate", "talk"}:
            session.current_time_minute += 5
        return {"current_time_minute": session.current_time_minute}
