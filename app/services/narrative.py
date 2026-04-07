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
    storage_refs: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


class NarrativeService:
    """承接 Engine 之后的 AI、软状态和文本落盘流程。"""

    def __init__(self, file_storage, runtime: NarrativeRuntime, fallback_runtime: NarrativeRuntime | None = None):
        self._file_storage = file_storage
        self._runtime = runtime
        self._fallback_runtime = fallback_runtime or FallbackNarrativeRuntime()

    def run(self, action: ActionRequest, session, engine_result, uow) -> NarrativeExecutionResult:
        context = self._build_context(action, session, engine_result, uow)
        runtime_result = self._run_runtime(engine_result, context)
        self._apply_soft_state_patch(context, runtime_result.soft_state_patch)

        storage_refs: dict[str, str] = {}
        ai_generation_log_path = self._append_ai_generation_log(session.uuid, action, engine_result, runtime_result)
        storage_refs["ai_generation_log"] = ai_generation_log_path
        dialogue = self._resolve_dialogue(engine_result, uow)
        if action.action_type == "talk" and engine_result.status == "accepted" and dialogue is not None:
            utterances = runtime_result.utterances or self._build_default_utterances(context, runtime_result)
            self._persist_utterances(dialogue, context, utterances)
            summary_text = runtime_result.dialogue_summary_text or self._build_default_summary(context, runtime_result)
            summary_path = self._file_storage.write_session_file(
                session.uuid,
                "dialogue/summaries",
                f"dialogue-{dialogue.id}.md",
                summary_text,
            )
            transcript_path = self._file_storage.write_session_file(
                session.uuid,
                "dialogue/transcripts",
                f"dialogue-{dialogue.id}.md",
                self._render_transcript(context, utterances),
            )
            dialogue.summary_file_path = summary_path
            dialogue.transcript_file_path = transcript_path
            storage_refs["dialogue_summary"] = summary_path
            storage_refs["dialogue_transcript"] = transcript_path
            self._apply_dialogue_updates(dialogue, runtime_result.soft_state_patch)
            self._persist_memory_updates(session.uuid, context, runtime_result, storage_refs)

        history_path = self._append_history(session.history_file_path, action, engine_result, runtime_result)
        latest_action_path = self._file_storage.write_session_history(
            session.uuid,
            "latest_action.json",
            json.dumps(
                {
                    "action_type": action.action_type,
                    "status": engine_result.status,
                    "current_time_minute": session.current_time_minute,
                    "narrative_text": runtime_result.narrative_text,
                    "metadata": runtime_result.metadata,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
            ),
        )
        storage_refs["history_markdown"] = history_path
        storage_refs["latest_action_log"] = latest_action_path
        return NarrativeExecutionResult(
            narrative_text=runtime_result.narrative_text,
            soft_state_patch=runtime_result.soft_state_patch,
            storage_refs=storage_refs,
            metadata=runtime_result.metadata,
        )

    def _build_context(self, action: ActionRequest, session, engine_result, uow) -> dict[str, Any]:
        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(action.session_id)}
        player = uow.players.get_by_session(action.session_id)
        dialogue_summary = engine_result.state_delta_summary.get("dialogue") or {}
        target_npc_key = dialogue_summary.get("target_npc_key") or action.payload.get("target_npc_key")
        target_npc = npcs.get(target_npc_key) if target_npc_key else None
        current_location = engine_result.scene_snapshot.details.get("current_location") or {}
        investigation = engine_result.state_delta_summary.get("investigation") or {}
        return {
            "session_id": action.session_id,
            "action_type": action.action_type,
            "session_uuid": session.uuid,
            "player": player,
            "npcs": npcs,
            "target_npc_key": target_npc_key,
            "target_npc": target_npc,
            "target_npc_name": target_npc.character.display_name if target_npc else None,
            "location_key": dialogue_summary.get("location_key") or current_location.get("key") or action.payload.get("target_location_key"),
            "location_name": current_location.get("name"),
            "dialogue_id": dialogue_summary.get("dialogue_id"),
            "discovered_clue_keys": [item.get("key") for item in investigation.get("discovered_clues", [])],
        }

    def _run_runtime(self, engine_result, context: dict[str, Any]) -> NarrativeRuntimeResult:
        try:
            return self._runtime.run(engine_result, context)
        except Exception as exc:
            fallback_result = self._fallback_runtime.run(engine_result, context)
            fallback_result.metadata["fallback_reason"] = exc.__class__.__name__
            return fallback_result

    def _append_ai_generation_log(
        self,
        session_uuid: str,
        action: ActionRequest,
        engine_result,
        runtime_result: NarrativeRuntimeResult,
    ) -> str:
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
        log_path = str(Path(self._file_storage.root) / "sessions" / session_uuid / "history" / "ai_generation_log.jsonl")
        return self._file_storage.append_text(
            log_path,
            json.dumps(log_entry, ensure_ascii=False) + "\n",
        )

    @staticmethod
    def _resolve_dialogue(engine_result, uow):
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

    @staticmethod
    def _build_default_summary(context: dict[str, Any], runtime_result: NarrativeRuntimeResult) -> str:
        return (
            f"dialogue summary: target={context.get('target_npc_key')}, "
            f"location={context.get('location_key')}, narrative={runtime_result.narrative_text}"
        )

    def _persist_utterances(self, dialogue, context: dict[str, Any], utterances: list[UtteranceDraft]) -> None:
        dialogue.utterances.clear()
        player_character = context["player"].character if context.get("player") else None
        target_npc = context.get("target_npc")
        for index, utterance in enumerate(utterances, start=1):
            speaker_character = target_npc.character if utterance.speaker_role == "npc" and target_npc else player_character
            if speaker_character is None:
                continue
            dialogue.utterances.append(
                UtteranceModel(
                    sequence_no=index,
                    speaker_character=speaker_character,
                    content=utterance.content,
                    tone_tag=utterance.tone_tag,
                    utterance_flags=utterance.utterance_flags,
                )
            )

    @staticmethod
    def _apply_dialogue_updates(dialogue, patch: SoftStatePatch) -> None:
        if "tag_flags" in patch.dialogue_updates:
            merged = dict(dialogue.tag_flags or {})
            merged.update(patch.dialogue_updates["tag_flags"])
            dialogue.tag_flags = merged

    @staticmethod
    def _apply_soft_state_patch(context: dict[str, Any], patch: SoftStatePatch) -> None:
        npcs = context.get("npcs") or {}
        for npc_key, updates in patch.npc_updates.items():
            npc = npcs.get(npc_key)
            if npc is None or npc.state is None:
                continue
            for field_name, value in updates.items():
                setattr(npc.state, field_name, value)

    def _persist_memory_updates(
        self,
        session_uuid: str,
        context: dict[str, Any],
        runtime_result: NarrativeRuntimeResult,
        storage_refs: dict[str, str],
    ) -> None:
        memory_updates = runtime_result.memory_updates or self._build_default_memory_updates(context, runtime_result)
        npcs = context.get("npcs") or {}
        for update in memory_updates:
            npc = npcs.get(update.npc_key)
            if npc is None or not npc.memory_file_path:
                continue
            previous_text = self._file_storage.read_text(npc.memory_file_path).rstrip()
            appended_section = f"\n\n## 本次对话更新\n{update.appended_text}\n"
            next_text = previous_text + appended_section if previous_text else appended_section.lstrip()
            path = self._file_storage.write_text(npc.memory_file_path, next_text)
            storage_refs[f"npc_memory:{update.npc_key}"] = path

    @staticmethod
    def _build_default_memory_updates(
        context: dict[str, Any],
        runtime_result: NarrativeRuntimeResult,
    ) -> list[NpcMemoryUpdate]:
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
    def _render_transcript(context: dict[str, Any], utterances: list[UtteranceDraft]) -> str:
        header = [
            f"# Dialogue Transcript",
            f"",
            f"- location: {context.get('location_key')}",
            f"- target_npc: {context.get('target_npc_key')}",
            f"",
        ]
        lines = header
        for utterance in utterances:
            lines.append(f"## {utterance.speaker_name}")
            lines.append(utterance.content)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _append_history(self, history_file_path: str | None, action: ActionRequest, engine_result, runtime_result: NarrativeRuntimeResult) -> str:
        target_path = history_file_path or self._file_storage.write_session_history(
            runtime_result.metadata.get("session_uuid", "unknown"),
            "HISTORY.md",
            "",
        )
        entry = (
            f"\n## {datetime.now(timezone.utc).isoformat()}\n"
            f"- action: {action.action_type}\n"
            f"- status: {engine_result.status}\n"
            f"- narrative: {runtime_result.narrative_text}\n"
        )
        return self._file_storage.append_text(target_path, entry)
