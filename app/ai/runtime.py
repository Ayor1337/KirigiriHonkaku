"""AI Runtime 实现。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.engine.service import EngineResult
from app.schemas.action import SoftStatePatch


@dataclass
class UtteranceDraft:
    """运行时生成的单条发言草稿。"""

    speaker_role: str
    speaker_name: str
    content: str
    tone_tag: str | None = None
    utterance_flags: dict[str, Any] = field(default_factory=dict)


@dataclass
class NpcMemoryUpdate:
    """需要写回到 NPC MEMORY.md 的增量文本。"""

    npc_key: str
    appended_text: str


@dataclass
class NarrativeRuntimeResult:
    """统一封装叙事运行时输出。"""

    narrative_text: str
    utterances: list[UtteranceDraft] = field(default_factory=list)
    dialogue_summary_text: str | None = None
    memory_updates: list[NpcMemoryUpdate] = field(default_factory=list)
    soft_state_patch: SoftStatePatch = field(default_factory=SoftStatePatch)
    metadata: dict[str, str] = field(default_factory=dict)


class NarrativeRuntime:
    """叙事运行时接口。"""

    def run(self, engine_result: EngineResult, context: dict[str, Any]) -> NarrativeRuntimeResult:
        raise NotImplementedError


class FallbackNarrativeRuntime(NarrativeRuntime):
    """不依赖外部 provider 的确定性叙事运行时。"""

    def run(self, engine_result: EngineResult, context: dict[str, Any]) -> NarrativeRuntimeResult:
        action_type = context["action_type"]
        status = engine_result.status
        location_key = context.get("location_key") or "unknown-location"

        if action_type == "talk" and status == "accepted":
            target_npc_key = context.get("target_npc_key") or "npc"
            target_npc_name = context.get("target_npc_name") or target_npc_key.title()
            narrative_text = f"{target_npc_name} 在 {location_key} 保持谨慎地回应了你的询问。"
            return NarrativeRuntimeResult(
                narrative_text=narrative_text,
                utterances=[
                    UtteranceDraft(
                        speaker_role="npc",
                        speaker_name=target_npc_name,
                        content=f"我现在只能告诉你，今晚在 {location_key} 一带确实不太平。",
                        tone_tag="guarded",
                        utterance_flags={"source": "fallback"},
                    )
                ],
                dialogue_summary_text=(
                    f"dialogue summary: target={target_npc_key}, location={location_key}, tone=guarded"
                ),
                memory_updates=[
                    NpcMemoryUpdate(
                        npc_key=target_npc_key,
                        appended_text=f"在 {location_key} 与玩家交谈后，对对方的调查意图保持警觉。",
                    )
                ],
                soft_state_patch=SoftStatePatch(
                    allowed=True,
                    npc_updates={
                        target_npc_key: {
                            "attitude_to_player": "guarded",
                            "emotion_tag": "wary",
                        }
                    },
                    dialogue_updates={"tag_flags": {"tone": "guarded", "source": "fallback"}},
                ),
                metadata={"runtime": "fallback"},
            )

        if action_type == "move" and status == "accepted":
            narrative_text = f"你已经移动到 {location_key}，现场气氛出现了新的变化。"
        elif action_type == "investigate" and status == "accepted":
            clue_keys = context.get("discovered_clue_keys") or []
            clue_segment = ", ".join(clue_keys) if clue_keys else "没有新的线索"
            narrative_text = f"你在 {location_key} 完成调查，结果是：{clue_segment}。"
        elif status == "rejected":
            error_text = "；".join(engine_result.errors) if engine_result.errors else "当前动作未能成立。"
            narrative_text = f"这次行动没有成功：{error_text}"
        else:
            narrative_text = f"系统已处理 {action_type} 动作。"

        return NarrativeRuntimeResult(
            narrative_text=narrative_text,
            metadata={"runtime": "fallback"},
        )


class OpenAiNarrativeRuntime(NarrativeRuntime):
    """基于 OpenAI 兼容 provider 的叙事运行时。"""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._timeout_seconds = timeout_seconds

    def run(self, engine_result: EngineResult, context: dict[str, Any]) -> NarrativeRuntimeResult:
        prompt = self._build_prompt(engine_result, context)
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
            timeout=self._timeout_seconds,
        )
        output_text = (getattr(response, "output_text", None) or "").strip()
        if not output_text:
            raise RuntimeError("OpenAI provider returned empty output")

        payload = self._parse_payload(output_text, context)
        return NarrativeRuntimeResult(
            narrative_text=payload["narrative_text"],
            utterances=[UtteranceDraft(**item) for item in payload.get("utterances", [])],
            dialogue_summary_text=payload.get("dialogue_summary_text"),
            memory_updates=[NpcMemoryUpdate(**item) for item in payload.get("memory_updates", [])],
            soft_state_patch=SoftStatePatch.model_validate(payload.get("soft_state_patch", {})),
            metadata={"runtime": "openai", "model": self._model},
        )

    @staticmethod
    def _build_prompt(engine_result: EngineResult, context: dict[str, Any]) -> str:
        return (
            "你是推理游戏后端的叙事运行时。\n"
            "请只在既定规则结果之后补写表达，不得改动硬状态。\n"
            "返回 JSON，字段包括 narrative_text、utterances、dialogue_summary_text、memory_updates、soft_state_patch。\n"
            f"动作类型: {context['action_type']}\n"
            f"动作状态: {engine_result.status}\n"
            f"当前地点: {context.get('location_key')}\n"
            f"目标 NPC: {context.get('target_npc_key')} / {context.get('target_npc_name')}\n"
            f"当前错误: {engine_result.errors}\n"
            "如果不是 talk，可省略 utterances / dialogue_summary_text / memory_updates。"
        )

    @staticmethod
    def _parse_payload(output_text: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError:
            target_npc_key = context.get("target_npc_key") or "npc"
            target_npc_name = context.get("target_npc_name") or target_npc_key.title()
            return {
                "narrative_text": output_text,
                "utterances": [
                    {
                        "speaker_role": "npc",
                        "speaker_name": target_npc_name,
                        "content": output_text,
                        "tone_tag": "neutral",
                        "utterance_flags": {"source": "openai_text_fallback"},
                    }
                ]
                if context.get("action_type") == "talk" and context.get("target_npc_key")
                else [],
                "dialogue_summary_text": output_text if context.get("action_type") == "talk" else None,
                "memory_updates": [],
                "soft_state_patch": {},
            }
        if not isinstance(payload, dict) or "narrative_text" not in payload:
            raise RuntimeError("OpenAI provider returned invalid JSON payload")
        return payload


def create_narrative_runtime(*, base_url: str, api_key: str | None, model: str | None, timeout_seconds: float) -> NarrativeRuntime:
    """根据配置创建当前活跃叙事运行时。"""

    if not api_key or not model:
        return FallbackNarrativeRuntime()
    return OpenAiNarrativeRuntime(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
