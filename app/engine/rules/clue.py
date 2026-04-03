"""线索规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class ClueRule:
    """为线索发现与归属变化预留统一入口。"""

    name = "clue"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """返回本次动作是否触发线索层检查。"""

        return {"clue_checked": action.action_type == "investigate"}
