"""Game Engine 主流程。"""

from dataclasses import dataclass

from app.engine.rules import AccusationRule, ClueRule, ExposureRule, MapRule, NpcScheduleRule, TimeRule
from app.models.session import SessionModel
from app.schemas.action import ActionRequest, AiTask, SceneSnapshot


@dataclass
class EngineResult:
    """封装引擎对一次 Action 的结构化结算结果。"""

    state_delta_summary: dict
    scene_snapshot: SceneSnapshot
    ai_tasks: list[AiTask]


class GameEngine:
    """统一调度规则模块的核心引擎。"""

    def __init__(self) -> None:
        self.modules = [
            TimeRule(),
            MapRule(),
            NpcScheduleRule(),
            ClueRule(),
            ExposureRule(),
            AccusationRule(),
        ]

    @property
    def module_names(self) -> list[str]:
        """返回已注册规则模块名，供测试和观测使用。"""

        return [module.name for module in self.modules]

    def process(self, action: ActionRequest, session: SessionModel) -> EngineResult:
        """按固定顺序处理 Action，并产出结构化结果骨架。"""

        module_outputs = {}
        for module in self.modules:
            module_outputs[module.name] = module.apply(action, session)

        scene_snapshot = SceneSnapshot(
            session_id=str(session.id),
            actor_id=action.actor_id,
            current_time_minute=session.current_time_minute,
            details={"action_payload": action.payload},
        )
        ai_tasks = [
            AiTask(
                task_name=f"{action.action_type}_narration",
                context={
                    "session_id": str(session.id),
                    "current_time_minute": session.current_time_minute,
                },
            )
        ]
        state_delta_summary = {
            "hard_state_updated": True,
            "current_time_minute": session.current_time_minute,
            "accusation_state": session.accusation_state,
            "module_outputs": module_outputs,
        }
        return EngineResult(
            state_delta_summary=state_delta_summary,
            scene_snapshot=scene_snapshot,
            ai_tasks=ai_tasks,
        )
