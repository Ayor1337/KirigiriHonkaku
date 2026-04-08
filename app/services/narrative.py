"""动作后的叙事编排服务。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.ai.runtime import (
    FallbackNarrativeRuntime,
    NarrativeRuntime,
    NarrativeRuntimeResult,
    NpcMemoryUpdate,
    UtteranceDraft,
)
from app.models.dialogue import UtteranceModel
from app.schemas.action import ActionRequest, SoftStatePatch


@dataclass
class NarrativeExecutionResult:
    """叙事后置链最终输出。"""

    narrative_text: str
    soft_state_patch: SoftStatePatch
    metadata: dict[str, str] = field(default_factory=dict)


class NarrativeService:
    """承接 Engine 之后的 AI、软状态和文本落盘流程。"""

    def __init__(self, runtime: NarrativeRuntime, fallback_runtime: NarrativeRuntime | None = None):
        """注入叙事生成依赖，并准备 provider 失败时的本地回退链路。"""

        self._runtime = runtime
        self._fallback_runtime = fallback_runtime or FallbackNarrativeRuntime()

    def run(self, action: ActionRequest, session, engine_result, uow) -> NarrativeExecutionResult:
        """执行动作后的叙事补写、软状态应用与文本落盘。"""

        context = self._build_context(action, session, engine_result, uow)
        runtime_result = self._run_runtime(engine_result, context)
        self._apply_soft_state_patch(context, runtime_result.soft_state_patch)

        self._append_ai_generation_log(session, action, engine_result, runtime_result)
        dialogue = self._resolve_dialogue(engine_result, uow)
        if action.action_type == "talk" and engine_result.status == "accepted" and dialogue is not None:
            utterances = self._compose_turn_utterances(context, runtime_result)
            self._persist_utterances(dialogue, context, utterances)
            dialogue.summary_markdown = runtime_result.dialogue_summary_text or self._build_default_summary(context, runtime_result)
            dialogue.transcript_markdown = self._render_transcript(dialogue, context)
            self._apply_dialogue_updates(dialogue, runtime_result.soft_state_patch)
            self._persist_memory_updates(context, runtime_result)

        session.history_markdown = self._append_history(session.history_markdown, action, engine_result, runtime_result)
        session.latest_action_payload = {
            "action_type": action.action_type,
            "status": engine_result.status,
            "current_time_minute": session.current_time_minute,
            "narrative_text": runtime_result.narrative_text,
            "metadata": runtime_result.metadata,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        return NarrativeExecutionResult(
            narrative_text=runtime_result.narrative_text,
            soft_state_patch=runtime_result.soft_state_patch,
            metadata=runtime_result.metadata,
        )

    def _build_context(self, action: ActionRequest, session, engine_result, uow) -> dict[str, Any]:
        """收集运行时生成叙事所需的最小上下文。"""

        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(action.session_id)}
        player = uow.players.get_by_session(action.session_id)
        dialogue_summary = engine_result.state_delta_summary.get("dialogue") or {}
        target_npc_key = dialogue_summary.get("target_npc_key") or action.payload.get("target_npc_key")
        target_npc = npcs.get(target_npc_key) if target_npc_key else None
        current_location = engine_result.scene_snapshot.details.get("current_location") or {}
        investigation = engine_result.state_delta_summary.get("investigation") or {}
        dialogue = self._resolve_dialogue(engine_result, uow)
        return {
            "session_id": action.session_id,
            "action_type": action.action_type,
            "session_uuid": session.uuid,
            "player": player,
            "player_text": action.payload.get("text"),
            "npcs": npcs,
            "target_npc_key": target_npc_key,
            "target_npc": target_npc,
            "target_npc_name": target_npc.character.display_name if target_npc else None,
            "location_key": dialogue_summary.get("location_key") or current_location.get("key") or action.payload.get("target_location_key"),
            "location_name": current_location.get("name"),
            "dialogue_id": dialogue_summary.get("dialogue_id"),
            "dialogue_history": self._serialize_dialogue_history(dialogue),
            "discovered_clue_keys": [item.get("key") for item in investigation.get("discovered_clues", [])],
        }

    def _run_runtime(self, engine_result, context: dict[str, Any]) -> NarrativeRuntimeResult:
        """优先调用外部叙事运行时，失败时回退到本地确定性实现。"""

        try:
            return self._runtime.run(engine_result, context)
        except Exception as exc:
            fallback_result = self._fallback_runtime.run(engine_result, context)
            fallback_result.metadata["fallback_reason"] = exc.__class__.__name__
            return fallback_result

    def _append_ai_generation_log(
        self,
        session,
        action: ActionRequest,
        engine_result,
        runtime_result: NarrativeRuntimeResult,
    ) -> None:
        """记录 AI 生成原文和结构化结果，便于排障。"""

        log_entry = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "action_type": action.action_type,
            "session_id": action.session_id,
            "status": engine_result.status,
            "runtime_metadata": runtime_result.metadata,
            "raw_output_text": runtime_result.raw_output_text or runtime_result.narrative_text,
            "result": {
                "narrative_text": runtime_result.narrative_text,
                "dialogue_summary_text": runtime_result.dialogue_summary_text,
                "utterances": [
                    {
                        "speaker_role": item.speaker_role,
                        "speaker_name": item.speaker_name,
                        "content": item.content,
                        "tone_tag": item.tone_tag,
                        "utterance_flags": item.utterance_flags,
                    }
                    for item in runtime_result.utterances
                ],
                "memory_updates": [
                    {
                        "npc_key": item.npc_key,
                        "appended_text": item.appended_text,
                    }
                    for item in runtime_result.memory_updates
                ],
                "soft_state_patch": runtime_result.soft_state_patch.model_dump(),
            },
        }
        session.ai_generation_log_entries = [*(session.ai_generation_log_entries or []), log_entry]

    @staticmethod
    def _resolve_dialogue(engine_result, uow):
        """根据引擎摘要回查当前动作对应的对话聚合。"""

        dialogue_summary = engine_result.state_delta_summary.get("dialogue") or {}
        dialogue_id = dialogue_summary.get("dialogue_id")
        if not dialogue_id:
            return None
        for dialogue in uow.dialogues.list_by_session(str(engine_result.scene_snapshot.session_id)):
            if str(dialogue.id) == dialogue_id:
                return dialogue
        return None

    @staticmethod
    def _build_default_utterances(context: dict[str, Any], runtime_result: NarrativeRuntimeResult) -> list[UtteranceDraft]:
        """当模型未返回发言列表时，为 NPC 构造一条保底回应。"""

        target_npc_name = context.get("target_npc_name") or "NPC"
        return [
            UtteranceDraft(
                speaker_role="npc",
                speaker_name=target_npc_name,
                content=runtime_result.narrative_text,
                tone_tag="neutral",
                utterance_flags={"source": "narrative-default"},
            )
        ]

    def _compose_turn_utterances(
        self,
        context: dict[str, Any],
        runtime_result: NarrativeRuntimeResult,
    ) -> list[UtteranceDraft]:
        """确保玩家输入和 NPC 回复可以组成完整的一回合对话。"""

        utterances = runtime_result.utterances or self._build_default_utterances(context, runtime_result)
        player_text = context.get("player_text")
        player = context.get("player")
        if not isinstance(player_text, str) or not player_text.strip() or player is None:
            return utterances
        if any(item.speaker_role == "player" for item in utterances):
            return utterances
        return [
            UtteranceDraft(
                speaker_role="player",
                speaker_name=player.character.display_name,
                content=player_text.strip(),
                tone_tag="probing",
                utterance_flags={"source": "player-input"},
            ),
            *utterances,
        ]

    @staticmethod
    def _build_default_summary(context: dict[str, Any], runtime_result: NarrativeRuntimeResult) -> str:
        """在模型未输出摘要时生成一条最小可用摘要。"""

        return (
            f"dialogue summary: target={context.get('target_npc_key')}, "
            f"location={context.get('location_key')}, narrative={runtime_result.narrative_text}"
        )

    def _persist_utterances(self, dialogue, context: dict[str, Any], utterances: list[UtteranceDraft]) -> None:
        """按顺序号把本回合发言落到对话聚合中。"""

        player_character = context["player"].character if context.get("player") else None
        target_npc = context.get("target_npc")
        next_sequence_no = max((item.sequence_no for item in dialogue.utterances), default=0) + 1
        for utterance in utterances:
            speaker_character = target_npc.character if utterance.speaker_role == "npc" and target_npc else player_character
            if speaker_character is None:
                continue
            dialogue.utterances.append(
                UtteranceModel(
                    sequence_no=next_sequence_no,
                    speaker_character=speaker_character,
                    content=utterance.content,
                    tone_tag=utterance.tone_tag,
                    utterance_flags=utterance.utterance_flags,
                )
            )
            next_sequence_no += 1

    @staticmethod
    def _apply_dialogue_updates(dialogue, patch: SoftStatePatch) -> None:
        """将模型返回的对话标签增量合并到现有聚合。"""

        if "tag_flags" in patch.dialogue_updates:
            merged = dict(dialogue.tag_flags or {})
            merged.update(patch.dialogue_updates["tag_flags"])
            dialogue.tag_flags = merged

    @staticmethod
    def _apply_soft_state_patch(context: dict[str, Any], patch: SoftStatePatch) -> None:
        """把允许的 NPC 软状态写回到当前工作单元中的对象图。"""

        npcs = context.get("npcs") or {}
        for npc_key, updates in patch.npc_updates.items():
            npc = npcs.get(npc_key)
            if npc is None or npc.state is None:
                continue
            for field_name, value in updates.items():
                setattr(npc.state, field_name, value)

    def _persist_memory_updates(
        self,
        context: dict[str, Any],
        runtime_result: NarrativeRuntimeResult,
    ) -> None:
        """把 NPC 记忆增量直接写回数据库字段。"""

        memory_updates = runtime_result.memory_updates or self._build_default_memory_updates(context, runtime_result)
        npcs = context.get("npcs") or {}
        for update in memory_updates:
            npc = npcs.get(update.npc_key)
            if npc is None:
                continue
            previous_text = (npc.memory_markdown or "").rstrip()
            appended_section = f"\n\n## 本次对话更新\n{update.appended_text}\n"
            npc.memory_markdown = previous_text + appended_section if previous_text else appended_section.lstrip()

    @staticmethod
    def _build_default_memory_updates(
        context: dict[str, Any],
        runtime_result: NarrativeRuntimeResult,
    ) -> list[NpcMemoryUpdate]:
        """在模型未显式给出记忆更新时，为目标 NPC 生成保底记录。"""

        target_npc_key = context.get("target_npc_key")
        if not target_npc_key:
            return []
        return [
            NpcMemoryUpdate(
                npc_key=target_npc_key,
                appended_text=f"记录：{runtime_result.narrative_text}",
            )
        ]

    @staticmethod
    def _serialize_dialogue_history(dialogue) -> list[dict[str, Any]]:
        """序列化既有对话历史，供模型续写时参考。"""

        if dialogue is None:
            return []
        return [
            {
                "sequence_no": utterance.sequence_no,
                "speaker_name": utterance.speaker_character.display_name,
                "speaker_role": "player" if utterance.speaker_character.kind == "player" else "npc",
                "content": utterance.content,
                "tone_tag": utterance.tone_tag,
            }
            for utterance in dialogue.utterances
        ]

    @staticmethod
    def _render_transcript(dialogue, context: dict[str, Any]) -> str:
        """把对话聚合渲染为便于人工查看的 Markdown 转录。"""

        header = [
            f"# Dialogue Transcript",
            f"",
            f"- location: {context.get('location_key')}",
            f"- target_npc: {context.get('target_npc_key')}",
            f"",
        ]
        lines = header
        for utterance in dialogue.utterances:
            lines.append(f"## {utterance.speaker_character.display_name}")
            lines.append(utterance.content)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _append_history(self, history_markdown: str | None, action: ActionRequest, engine_result, runtime_result: NarrativeRuntimeResult) -> str:
        """向会话历史正文追加本次动作的最小执行记录。"""

        entry = (
            f"\n## {datetime.now(timezone.utc).isoformat()}\n"
            f"- action: {action.action_type}\n"
            f"- status: {engine_result.status}\n"
            f"- narrative: {runtime_result.narrative_text}\n"
        )
        return f"{history_markdown or ''}{entry}"
