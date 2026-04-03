"""暴露度规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class ExposureRule:
    """为暴露度变化结算保留稳定接口。"""

    name = "exposure"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """返回当前暴露度主值。"""

        return {"exposure_value": context.session.exposure_value}
