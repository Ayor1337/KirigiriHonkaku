"""暴露度规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class ExposureRule:
    """处理暴露度推进与最小风险反制。"""

    name = "exposure"

    EXPOSURE_BY_ACTION = {
        "investigate": 1,
        "gather": 1,
        "accuse": 2,
    }

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """推进暴露度，并在中高风险阶段触发最小反制。"""

        previous_value = context.session.exposure_value
        previous_level = context.session.exposure_level or self._resolve_level(previous_value)
        delta = 0

        if context.accepted:
            delta = self.EXPOSURE_BY_ACTION.get(action.action_type, 0)
            context.session.exposure_value += delta
            context.session.exposure_level = self._resolve_level(context.session.exposure_value)
            if context.player.state is not None:
                context.player.state.exposure_value = context.session.exposure_value
                context.player.state.exposure_level = context.session.exposure_level

        current_level = context.session.exposure_level or previous_level
        risk = self._apply_countermeasure(context, previous_level, current_level, delta)
        return {
            "exposure": {
                "previous_value": previous_value,
                "value": context.session.exposure_value,
                "delta": delta,
                "previous_level": previous_level,
                "level": current_level,
            },
            "risk": risk,
            "exposure_value": context.session.exposure_value,
        }

    @staticmethod
    def _resolve_level(value: int) -> str:
        if value >= 4:
            return "high"
        if value >= 2:
            return "medium"
        return "low"

    def _apply_countermeasure(
        self,
        context: ActionExecutionContext,
        previous_level: str,
        current_level: str,
        delta: int,
    ) -> dict:
        culprit = self._resolve_culprit(context)
        if culprit is None or culprit.state is None:
            return {
                "countermeasure_triggered": False,
                "mode": None,
                "affected_npc_keys": [],
            }

        if current_level == "low":
            return {
                "countermeasure_triggered": False,
                "mode": None,
                "affected_npc_keys": [],
            }

        culprit.state.is_under_pressure = True
        culprit.state.alertness_level = "high" if current_level == "high" else "medium"
        culprit.state.state_flags = {
            **culprit.state.state_flags,
            "countermeasure_mode": "direct" if current_level == "high" else "indirect",
        }
        triggered = current_level != previous_level or delta > 0
        return {
            "countermeasure_triggered": triggered,
            "mode": culprit.state.state_flags["countermeasure_mode"],
            "affected_npc_keys": [culprit.template_key],
        }

    @staticmethod
    def _resolve_culprit(context: ActionExecutionContext):
        culprit_key = (context.session.truth_payload or {}).get("culprit_npc_key")
        if not culprit_key:
            return None
        return next((npc for npc in context.npcs if npc.template_key == culprit_key), None)
