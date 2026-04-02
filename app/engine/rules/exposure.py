"""暴露度规则模块。"""

from app.models.session import SessionModel
from app.schemas.action import ActionRequest


class ExposureRule:
    """为暴露度变化结算保留稳定接口。"""

    name = "exposure"

    def apply(self, action: ActionRequest, session: SessionModel) -> dict:
        """返回当前暴露度主值。"""

        return {"exposure_value": session.exposure_value}
