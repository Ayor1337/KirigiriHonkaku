"""NPC 调度规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class NpcScheduleRule:
    """为 NPC 日程推进预留统一入口。"""

    name = "npc_schedule"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """返回本次动作是否需要检查 NPC 日程。"""

        return {"npc_schedule_checked": action.action_type in {"move", "talk"}}
