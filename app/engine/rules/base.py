"""规则模块协议定义。"""

from typing import Protocol

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class RuleModule(Protocol):
    """所有规则模块都需要实现的最小接口。"""

    name: str

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        ...
