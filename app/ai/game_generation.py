"""多轮 AGENT 游戏生成运行时。"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.schemas.world_generation import GameGenerationPlan, WorldBlueprint

ProgressCallback = Callable[[str, dict[str, Any]], None] | None


class GameGenerationProviderError(RuntimeError):
    """模型 provider 不可用或调用失败。"""


class GameGenerationOutputError(RuntimeError):
    """模型输出不是可解析的结构化结果。"""


class GameGenerationBlueprintValidationError(RuntimeError):
    """模型输出结构合法但不满足本地业务约束。"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class GameGenerationRuntime:
    """完整游戏生成运行时接口。"""

    def generate(self, *, session_uuid: str, progress_callback: ProgressCallback = None) -> WorldBlueprint:
        raise NotImplementedError


class UnavailableGameGenerationRuntime(GameGenerationRuntime):
    """在未配置模型时给出显式失败。"""

    def generate(self, *, session_uuid: str, progress_callback: ProgressCallback = None) -> WorldBlueprint:
        raise GameGenerationProviderError("Game generation runtime is not configured.")


class OpenAiGameGenerationRuntime(GameGenerationRuntime):
    """基于 OpenAI 兼容 provider 的多轮游戏生成器。"""

    MAX_FIX_ATTEMPTS = 2

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate(self, *, session_uuid: str, progress_callback: ProgressCallback = None) -> WorldBlueprint:
        self._emit_progress(progress_callback, "world_planning")
        plan = self._generate_plan(session_uuid)

        self._emit_progress(progress_callback, "world_generating")
        payload = self._normalize_blueprint_payload(self._request_json(self._build_blueprint_prompt(session_uuid, plan)))

        attempt = 1
        max_attempts = self.MAX_FIX_ATTEMPTS + 1
        self._emit_progress(
            progress_callback,
            "world_validating",
            {"attempt": attempt, "max_attempts": max_attempts},
        )
        blueprint, errors = self._coerce_blueprint(payload)

        while attempt <= self.MAX_FIX_ATTEMPTS and (blueprint is None or errors):
            self._emit_progress(
                progress_callback,
                "world_fixing",
                {"attempt": attempt, "max_attempts": max_attempts},
            )
            payload = self._normalize_blueprint_payload(
                self._request_json(self._build_fix_prompt(session_uuid, plan, payload, errors))
            )
            attempt += 1
            self._emit_progress(
                progress_callback,
                "world_validating",
                {"attempt": attempt, "max_attempts": max_attempts},
            )
            blueprint, errors = self._coerce_blueprint(payload)

        if blueprint is not None and not errors:
            return blueprint
        raise GameGenerationBlueprintValidationError(errors)

    def _generate_plan(self, session_uuid: str) -> GameGenerationPlan:
        payload = self._normalize_plan_payload(self._request_json(self._build_plan_prompt(session_uuid)))
        try:
            return GameGenerationPlan.model_validate(payload)
        except ValidationError as exc:
            raise GameGenerationOutputError(self._format_validation_error(exc)) from exc

    def _coerce_blueprint(self, payload: dict[str, Any]) -> tuple[WorldBlueprint | None, list[str]]:
        try:
            blueprint = WorldBlueprint.model_validate(payload)
        except ValidationError as exc:
            return None, [self._format_validation_error(exc)]
        errors = validate_world_blueprint(blueprint)
        return blueprint, errors

    def _request_json(self, prompt: str) -> dict[str, Any]:
        output_text = self._request_text(prompt)
        normalized_output = self._normalize_json_text(output_text)
        try:
            payload = json.loads(normalized_output)
        except json.JSONDecodeError as exc:
            raise GameGenerationOutputError("Model returned non-JSON output.") from exc
        if not isinstance(payload, dict):
            raise GameGenerationOutputError("Model returned a non-object JSON payload.")
        return payload

    def _request_text(self, prompt: str) -> str:
        try:
            return self._request_text_via_responses(prompt)
        except Exception as exc:
            if self._should_fallback_to_chat(exc):
                try:
                    return self._request_text_via_chat(prompt)
                except Exception as fallback_exc:
                    raise GameGenerationProviderError(self._format_provider_error(fallback_exc)) from fallback_exc
            raise GameGenerationProviderError(self._format_provider_error(exc)) from exc

    def _request_text_via_responses(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
            timeout=self._timeout_seconds,
        )
        output_text = (getattr(response, "output_text", None) or "").strip()
        if not output_text:
            raise GameGenerationOutputError("Model returned empty output.")
        return output_text

    def _request_text_via_chat(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._timeout_seconds,
        )
        output_text = self._extract_chat_content(response)
        if not output_text:
            raise GameGenerationOutputError("Model returned empty output.")
        return output_text

    @staticmethod
    def _extract_chat_content(response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                else:
                    text = getattr(item, "text", None) or getattr(item, "content", None) or ""
                if text:
                    parts.append(str(text))
            return "\n".join(parts).strip()
        return ""

    @staticmethod
    def _should_fallback_to_chat(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code == 404:
            return True
        return "notfound" in exc.__class__.__name__.lower()

    @staticmethod
    def _normalize_json_text(output_text: str) -> str:
        text = output_text.strip()
        if not text.startswith("```"):
            return text
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _normalize_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        bounds = {
            "target_location_count": (3, 8),
            "target_npc_count": (2, 6),
            "target_clue_count": (2, 8),
            "target_event_count": (1, 4),
        }
        for key, (minimum, maximum) in bounds.items():
            value = normalized.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                normalized[key] = min(max(value, minimum), maximum)
        return normalized

    @classmethod
    def _normalize_blueprint_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized["map"] = cls._normalize_map_payload(payload.get("map"), payload.get("title"))
        normalized["locations"] = [cls._normalize_location_payload(item) for item in payload.get("locations", [])]
        normalized["connections"] = [cls._normalize_connection_payload(item) for item in payload.get("connections", [])]
        normalized["player"] = cls._normalize_player_payload(payload.get("player"))
        normalized["npcs"] = [cls._normalize_npc_payload(item) for item in payload.get("npcs", [])]
        normalized["clues"] = [cls._normalize_clue_payload(item) for item in payload.get("clues", [])]
        normalized["events"] = [cls._normalize_event_payload(item) for item in payload.get("events", [])]
        normalized["truth"] = cls._normalize_truth_payload(payload.get("truth"))
        return normalized

    @staticmethod
    def _normalize_map_payload(payload: Any, title: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "display_name": payload.get("display_name") or payload.get("name") or title or "案件地图",
        }
        if "template_key" in payload:
            normalized["template_key"] = payload["template_key"]
        return normalized

    @staticmethod
    def _normalize_location_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "key": payload.get("key"),
            "name": payload.get("name") or payload.get("display_name") or payload.get("key"),
            "location_type": payload.get("location_type") or payload.get("type") or "room",
        }
        description = payload.get("description") or payload.get("atmosphere")
        if description is not None:
            normalized["description"] = description
        for key in ("parent_key", "visibility_level", "is_hidden", "status_flags"):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @staticmethod
    def _normalize_connection_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "from_location_key": payload.get("from_location_key") or payload.get("from_key"),
            "to_location_key": payload.get("to_location_key") or payload.get("to_key"),
        }
        for key in (
            "connection_type",
            "access_rule",
            "is_hidden",
            "is_locked",
            "is_one_way",
            "is_dangerous",
            "time_window_rule",
        ):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @staticmethod
    def _normalize_player_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "display_name": payload.get("display_name") or payload.get("name") or "Player",
            "start_location_key": payload.get("start_location_key") or payload.get("location_key"),
        }
        for key in (
            "public_identity",
            "template_key",
            "template_name",
            "trait_text",
            "background_text",
            "unlocked_access",
            "status_flags",
        ):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @classmethod
    def _normalize_npc_payload(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "key": payload.get("key"),
            "display_name": payload.get("display_name") or payload.get("name") or payload.get("key"),
            "location_key": payload.get("location_key") or payload.get("start_location_key"),
            "profile_markdown": payload.get("profile_markdown") or payload.get("profile") or "",
            "memory_markdown": payload.get("memory_markdown") or payload.get("memory") or "",
        }
        for key in (
            "public_identity",
            "role_type",
            "attitude_to_player",
            "alertness_level",
            "emotion_tag",
            "schedule_mode",
        ):
            if key in payload:
                normalized[key] = payload[key]
        if isinstance(payload.get("schedule_entries"), list):
            normalized["schedule_entries"] = [cls._normalize_schedule_entry_payload(item) for item in payload["schedule_entries"]]
        return normalized

    @staticmethod
    def _normalize_schedule_entry_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "start_minute": payload.get("start_minute"),
            "end_minute": payload.get("end_minute"),
            "behavior_type": payload.get("behavior_type") or payload.get("type") or "idle",
            "target_location_key": payload.get("target_location_key") or payload.get("location_key"),
        }
        for key in ("behavior_description", "priority"):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @staticmethod
    def _normalize_clue_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        initial_location_key = payload.get("initial_location_key")
        current_location_key = payload.get("current_location_key")
        initial_holder_key = payload.get("initial_holder_character_key") or payload.get("initial_holder_key")
        current_holder_key = payload.get("current_holder_character_key") or payload.get("current_holder_key")
        shared_location_key = payload.get("location_key")
        shared_holder_key = payload.get("holder_key")
        if initial_location_key is None and current_location_key is None and shared_location_key is not None:
            initial_location_key = shared_location_key
            current_location_key = shared_location_key
        if initial_holder_key is None and current_holder_key is None and shared_holder_key is not None:
            initial_holder_key = shared_holder_key
            current_holder_key = shared_holder_key
        normalized = {
            "key": payload.get("key"),
            "name": payload.get("name") or payload.get("display_name") or payload.get("key"),
            "clue_type": payload.get("clue_type") or payload.get("type") or "document",
            "initial_location_key": initial_location_key,
            "initial_holder_character_key": initial_holder_key,
            "current_location_key": current_location_key,
            "current_holder_character_key": current_holder_key,
            "document_markdown": payload.get("document_markdown") or payload.get("document") or "",
        }
        for key in (
            "description",
            "is_key_clue",
            "is_movable",
            "is_time_sensitive",
            "clue_state",
            "discovery_rule",
        ):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @classmethod
    def _normalize_event_payload(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "name": payload.get("name") or payload.get("display_name") or payload.get("key"),
            "event_type": payload.get("event_type") or payload.get("type") or "story_event",
            "location_key": payload.get("location_key") or payload.get("target_location_key"),
            "start_minute": payload.get("start_minute"),
            "end_minute": payload.get("end_minute"),
        }
        description = payload.get("description") or payload.get("effect_markdown")
        if description is not None:
            normalized["description"] = description
        for key in ("event_state", "is_public_event", "rule_flags"):
            if key in payload:
                normalized[key] = payload[key]
        if "trigger_condition" in payload:
            normalized.setdefault("rule_flags", {})
            if isinstance(normalized["rule_flags"], dict):
                normalized["rule_flags"] = dict(normalized["rule_flags"])
                normalized["rule_flags"]["trigger_condition"] = payload["trigger_condition"]
        if isinstance(payload.get("participants"), list):
            normalized["participants"] = [cls._normalize_event_participant_payload(item) for item in payload["participants"]]
        return normalized

    @staticmethod
    def _normalize_event_participant_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "character_key": payload.get("character_key") or payload.get("npc_key") or payload.get("participant_key"),
        }
        for key in ("participant_role", "attendance_state"):
            if key in payload:
                normalized[key] = payload[key]
        return normalized

    @staticmethod
    def _normalize_truth_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = {
            "culprit_npc_key": payload.get("culprit_npc_key"),
            "required_clue_keys": payload.get("required_clue_keys", []),
            "supporting_clue_keys": payload.get("supporting_clue_keys", []),
            "false_verdict_targets": payload.get("false_verdict_targets", []),
            "public_accusation_event_keys": payload.get("public_accusation_event_keys", []),
            "countermeasure_plan": payload.get("countermeasure_plan", {}),
            "private_encounter_rules": payload.get("private_encounter_rules", {}),
        }
        return normalized

    @staticmethod
    def _format_provider_error(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        body = getattr(exc, "body", None)
        message = str(exc).strip()
        parts = [f"Provider call failed: {exc.__class__.__name__}"]
        if status_code is not None:
            parts.append(f"status={status_code}")
        if message:
            parts.append(f"message={message}")
        elif body is not None:
            parts.append(f"body={body}")
        if "timeout" in exc.__class__.__name__.lower() or "timed out" in message.lower():
            parts.append("hint=Increase KIRIGIRI_OPENAI_GAME_GENERATION_TIMEOUT_SECONDS for bootstrap requests.")
        return "; ".join(parts)

    @staticmethod
    def _format_validation_error(exc: ValidationError) -> str:
        parts = []
        for item in exc.errors():
            loc = ".".join(str(part) for part in item["loc"])
            parts.append(f"{loc}: {item['msg']}")
        return "; ".join(parts)

    @staticmethod
    def _build_plan_prompt(session_uuid: str) -> str:
        return (
            "你是本格推理游戏的世界规划 Agent。\n"
            "请基于给定的 session_uuid 生成一个随机但完整可玩的案件规划。\n"
            "必须只返回 JSON 对象，不得输出 Markdown 或解释。\n"
            "JSON 字段必须严格包含："
            "title,premise,setting,tone,target_location_count,target_npc_count,target_clue_count,target_event_count。\n"
            "要求：\n"
            "- title 是具体案件标题。\n"
            "- premise 概括案件核心冲突与真相方向。\n"
            "- setting 描述时代/场景。\n"
            "- tone 描述整体气质。\n"
            "- target_location_count 必须在 3 到 8 之间。\n"
            "- target_npc_count 必须在 2 到 6 之间。\n"
            "- target_clue_count 必须在 2 到 8 之间。\n"
            "- target_event_count 必须在 1 到 4 之间。\n"
            "- 各 count 必须与最终可玩规模匹配。\n"
            f"session_uuid: {session_uuid}\n"
        )

    @staticmethod
    def _build_blueprint_prompt(session_uuid: str, plan: GameGenerationPlan) -> str:
        return (
            "你是本格推理游戏的世界生成 Agent。\n"
            "请根据规划生成完整可玩的游戏世界蓝图。\n"
            "必须只返回 JSON 对象，不得输出解释。\n"
            "输出必须满足当前后端可消费的结构，顶层字段必须严格包含："
            "title,map,locations,connections,player,npcs,clues,events,truth。\n"
            "字段契约：\n"
            "- map 只能包含：display_name, template_key。\n"
            "- location 必须使用 name，不得使用 display_name；字段只能是 key,name,description,location_type,parent_key,visibility_level,is_hidden,status_flags。\n"
            "- player 只能包含 display_name,public_identity,template_key,template_name,trait_text,background_text,start_location_key,unlocked_access,status_flags。\n"
            "- clue 必须使用 name，不得使用 display_name；持有者字段必须是 initial_holder_character_key / current_holder_character_key。\n"
            "- event 必须使用 name，不得输出 key 或 display_name；字段只能是 name,event_type,description,location_key,start_minute,end_minute,event_state,is_public_event,rule_flags,participants。\n"
            "- truth 只能包含 culprit_npc_key,required_clue_keys,supporting_clue_keys,false_verdict_targets,public_accusation_event_keys,countermeasure_plan,private_encounter_rules。\n"
            "- 禁止输出 atmosphere, method_markdown, fate_markdown, trigger_condition 这类契约外字段。\n"
            "约束：\n"
            "- locations 的 key 唯一。\n"
            "- connections 的 from_location_key / to_location_key 必须引用已存在地点。\n"
            "- player.start_location_key 与 npc.location_key 必须引用已存在地点。\n"
            "- clues 必须满足初始持有者与初始地点二选一，当前持有者与当前位置二选一。\n"
            "- truth.culprit_npc_key 必须引用某个 npc.key。\n"
            "- truth.required_clue_keys 至少包含一个 clue.key。\n"
            "- npc.profile_markdown、npc.memory_markdown、clue.document_markdown 不能为空字符串。\n"
            "- 保持线索、事件与真相之间的逻辑闭环，确保 public/private accuse 都可运行。\n"
            f"session_uuid: {session_uuid}\n"
            f"plan: {plan.model_dump_json()}\n"
        )

    @staticmethod
    def _build_fix_prompt(
        session_uuid: str,
        plan: GameGenerationPlan,
        payload: dict[str, Any],
        errors: list[str],
    ) -> str:
        return (
            "你是本格推理游戏的世界修正 Agent。\n"
            "下面是之前生成的世界蓝图与校验错误，请修复后重新输出完整 JSON 对象。\n"
            "不要解释，只输出修正后的 JSON 对象。\n"
            "修正时必须严格遵守字段契约：location/clue/event 使用 name，不要使用 display_name；"
            "event 不得输出 key；持有者字段使用 initial_holder_character_key / current_holder_character_key；"
            "不要输出 atmosphere、method_markdown、fate_markdown、trigger_condition 等额外字段。\n"
            f"session_uuid: {session_uuid}\n"
            f"plan: {plan.model_dump_json()}\n"
            f"errors: {json.dumps(errors, ensure_ascii=False)}\n"
            f"invalid_blueprint: {json.dumps(payload, ensure_ascii=False)}\n"
        )

    @staticmethod
    def _emit_progress(progress_callback: ProgressCallback, placeholder: str, payload: dict[str, Any] | None = None) -> None:
        if progress_callback is None:
            return
        progress_callback(placeholder, payload or {})


def validate_world_blueprint(blueprint: WorldBlueprint) -> list[str]:
    """执行本地业务校验，确保蓝图可被当前引擎消费。"""

    errors: list[str] = []
    location_keys = [location.key for location in blueprint.locations]
    npc_keys = [npc.key for npc in blueprint.npcs]
    clue_keys = [clue.key for clue in blueprint.clues]
    event_names = [event.name for event in blueprint.events]
    location_key_set = set(location_keys)
    npc_key_set = set(npc_keys)
    clue_key_set = set(clue_keys)

    if len(location_key_set) != len(location_keys):
        errors.append("locations.key must be unique.")
    if len(npc_key_set) != len(npc_keys):
        errors.append("npcs.key must be unique.")
    if len(clue_key_set) != len(clue_keys):
        errors.append("clues.key must be unique.")

    if blueprint.player.start_location_key not in location_key_set:
        errors.append("player.start_location_key must reference an existing location.")
    for access_key in blueprint.player.unlocked_access:
        if access_key not in location_key_set:
            errors.append(f"player.unlocked_access contains unknown location: {access_key}.")

    for location in blueprint.locations:
        if location.parent_key and location.parent_key not in location_key_set:
            errors.append(f"location {location.key} references unknown parent_key {location.parent_key}.")

    for connection in blueprint.connections:
        if connection.from_location_key not in location_key_set:
            errors.append(f"connection.from_location_key references unknown location {connection.from_location_key}.")
        if connection.to_location_key not in location_key_set:
            errors.append(f"connection.to_location_key references unknown location {connection.to_location_key}.")

    for npc in blueprint.npcs:
        if npc.location_key not in location_key_set:
            errors.append(f"npc {npc.key} references unknown location {npc.location_key}.")
        if not npc.profile_markdown.strip():
            errors.append(f"npc {npc.key} requires non-empty profile_markdown.")
        if not npc.memory_markdown.strip():
            errors.append(f"npc {npc.key} requires non-empty memory_markdown.")
        for entry in npc.schedule_entries:
            if entry.target_location_key not in location_key_set:
                errors.append(f"npc {npc.key} schedule references unknown location {entry.target_location_key}.")

    known_character_keys = {"player", *npc_key_set}
    for clue in blueprint.clues:
        initial_refs = sum(value is not None for value in (clue.initial_location_key, clue.initial_holder_character_key))
        current_refs = sum(value is not None for value in (clue.current_location_key, clue.current_holder_character_key))
        if initial_refs != 1:
            errors.append(f"clue {clue.key} must set exactly one initial owner reference.")
        if current_refs != 1:
            errors.append(f"clue {clue.key} must set exactly one current owner reference.")
        if clue.initial_location_key and clue.initial_location_key not in location_key_set:
            errors.append(f"clue {clue.key} initial_location_key references unknown location.")
        if clue.current_location_key and clue.current_location_key not in location_key_set:
            errors.append(f"clue {clue.key} current_location_key references unknown location.")
        if clue.initial_holder_character_key and clue.initial_holder_character_key not in known_character_keys:
            errors.append(f"clue {clue.key} initial_holder_character_key references unknown character.")
        if clue.current_holder_character_key and clue.current_holder_character_key not in known_character_keys:
            errors.append(f"clue {clue.key} current_holder_character_key references unknown character.")
        if not clue.document_markdown.strip():
            errors.append(f"clue {clue.key} requires non-empty document_markdown.")

    for event in blueprint.events:
        if event.location_key not in location_key_set:
            errors.append(f"event {event.name} references unknown location {event.location_key}.")
        for participant in event.participants:
            if participant.character_key not in known_character_keys:
                errors.append(f"event {event.name} participant references unknown character {participant.character_key}.")

    truth = blueprint.truth
    if truth.culprit_npc_key not in npc_key_set:
        errors.append("truth.culprit_npc_key must reference an existing npc.")
    if not truth.required_clue_keys:
        errors.append("truth.required_clue_keys must contain at least one clue key.")
    for clue_key in [*truth.required_clue_keys, *truth.supporting_clue_keys]:
        if clue_key not in clue_key_set:
            errors.append(f"truth references unknown clue key {clue_key}.")
    for npc_key in truth.false_verdict_targets:
        if npc_key not in npc_key_set:
            errors.append(f"truth.false_verdict_targets references unknown npc {npc_key}.")
    for event_key in truth.public_accusation_event_keys:
        if event_key not in event_names:
            errors.append(f"truth.public_accusation_event_keys references unknown event {event_key}.")
    if "indirect" not in truth.countermeasure_plan or "direct" not in truth.countermeasure_plan:
        errors.append("truth.countermeasure_plan must contain indirect and direct arrays.")
    if "violent_flag" not in truth.private_encounter_rules or "fabricate_flag" not in truth.private_encounter_rules:
        errors.append("truth.private_encounter_rules must contain violent_flag and fabricate_flag.")

    return errors


def create_game_generation_runtime(
    *,
    base_url: str,
    api_key: str | None,
    model: str | None,
    timeout_seconds: float,
) -> GameGenerationRuntime:
    """根据配置创建完整游戏生成运行时。"""

    if not api_key or not model:
        return UnavailableGameGenerationRuntime()
    return OpenAiGameGenerationRuntime(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
