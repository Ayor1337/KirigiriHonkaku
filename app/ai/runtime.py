"""AI Runtime 骨架实现。"""

from app.engine.service import EngineResult
from app.schemas.action import SoftStatePatch


class AiRuntimeResult:
    """封装 AI Runtime 的结构化输出。"""

    def __init__(self, soft_state_patch: SoftStatePatch, generated_text: str) -> None:
        self.soft_state_patch = soft_state_patch
        self.generated_text = generated_text


class StubAiRuntime:
    """用于 Step 1 的占位 AI Runtime，不接真实模型。"""

    def run(self, engine_result: EngineResult) -> AiRuntimeResult:
        """根据引擎输出返回最小可用的软状态 patch 与文本结果。"""

        updates = {"emotion_tag": "steady"}
        patch = SoftStatePatch(allowed=True, updates=updates)
        return AiRuntimeResult(
            soft_state_patch=patch,
            generated_text=f"AI stub generated {engine_result.ai_tasks[0].task_name}",
        )
