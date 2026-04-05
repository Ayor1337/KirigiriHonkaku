"""指认与结局规则模块。"""

from __future__ import annotations

from app.engine.rules.base import ActionExecutionContext
from app.models.event import EventModel, EventParticipantModel
from app.schemas.action import ActionRequest


class AccusationRule:
    """处理公开场合、正式指认与结局分流。"""

    name = "accusation"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """处理 gather/accuse，并返回统一结案摘要。"""

        public_context = self._resolve_public_context(context)
        accusation = {
            "state": context.session.accusation_state,
            "resolution": None,
            "requested_context_mode": action.payload.get("context_mode") if action.action_type == "accuse" else None,
            "resolved_context_mode": "public" if public_context["is_public"] else "private",
            "target_npc_key": getattr(context.resolved_target_npc, "template_key", None),
        }
        ending = {
            "ending_type": context.session.ending_type,
            "session_status": context.session.status,
        }

        if not context.accepted or action.action_type not in {"gather", "accuse"}:
            return {
                "accusation_state": context.session.accusation_state,
                "accusation": accusation,
                "public_context": public_context,
                "ending": ending,
            }

        if action.action_type == "gather":
            public_context = self._create_public_gathering(action, context)
            accusation["state"] = context.session.accusation_state
            accusation["resolved_context_mode"] = "public"
            return {
                "accusation_state": context.session.accusation_state,
                "accusation": accusation,
                "public_context": public_context,
                "ending": ending,
            }

        result = self._resolve_accusation(action, context, public_context)
        return {
            "accusation_state": context.session.accusation_state,
            "accusation": result["accusation"],
            "public_context": result["public_context"],
            "ending": result["ending"],
        }

    def _create_public_gathering(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return self._resolve_public_context(context)

        event_key = f"gather-{current_location.key}-{context.session.current_time_minute}"
        event = EventModel(
            session=context.session,
            name="Player Gathering",
            event_type="player_gathering",
            description=action.payload.get("reason") or "玩家主动召集众人形成公开场合。",
            location=current_location,
            start_minute=context.session.current_time_minute,
            end_minute=context.session.current_time_minute + 15,
            event_state="active",
            is_public_event=True,
            rule_flags={
                "public_context_key": event_key,
                "source": "gather",
                "reason": action.payload.get("reason"),
            },
        )
        event.participants.append(
            EventParticipantModel(
                character=context.player.character,
                participant_role="organizer",
                attendance_state="present",
            )
        )
        for npc in context.npcs:
            if npc.state is None or npc.state.current_location_id != current_location.id or not npc.state.is_available:
                continue
            event.participants.append(
                EventParticipantModel(
                    character=npc.character,
                    participant_role="witness",
                    attendance_state="present",
                )
            )
            npc.state.is_in_event = True

        context.session.events.append(event)
        context.events.append(event)
        context.created_event = event
        return self._resolve_public_context(context)

    def _resolve_accusation(self, action: ActionRequest, context: ActionExecutionContext, public_context: dict) -> dict:
        target_npc = context.resolved_target_npc
        target_key = target_npc.template_key if target_npc is not None else None
        truth = context.session.truth_payload or {}
        culprit_key = truth.get("culprit_npc_key")
        context.session.accusation_state = "submitted"

        resolved_mode = "public" if public_context["is_public"] else "private"
        force_strategy = action.payload.get("force_strategy") or "standard"
        accusation = {
            "state": context.session.accusation_state,
            "resolution": None,
            "requested_context_mode": action.payload.get("context_mode"),
            "resolved_context_mode": resolved_mode,
            "target_npc_key": target_key,
        }

        if resolved_mode == "private":
            if target_key == culprit_key:
                if force_strategy == "violent" and self._player_flag_enabled(context, "can_counterattack_culprit"):
                    ending_type = "pseudo_victory_kill_culprit"
                    accusation["resolution"] = "violent_resolution"
                else:
                    ending_type = "failure_killed_by_culprit"
                    accusation["resolution"] = "culprit_counterattack"
            else:
                ending_type = "failure_wrong_accusation"
                accusation["resolution"] = "wrong_target"
            return self._finalize_ending(context, accusation, public_context, ending_type)

        if force_strategy == "fabricate":
            if self._player_flag_enabled(context, "can_fabricate_evidence") and target_key in truth.get("false_verdict_targets", []):
                accusation["resolution"] = "fabricated_verdict"
                return self._finalize_ending(context, accusation, public_context, "pseudo_victory_false_verdict")
            accusation["resolution"] = "fabricate_failed"
            return self._finalize_ending(context, accusation, public_context, "failure_wrong_accusation")

        if target_key != culprit_key:
            accusation["resolution"] = "wrong_target"
            return self._finalize_ending(context, accusation, public_context, "failure_wrong_accusation")

        if self._has_required_evidence(action, context, truth):
            accusation["resolution"] = "success"
            return self._finalize_ending(context, accusation, public_context, "success")

        accusation["resolution"] = "insufficient_evidence"
        return self._finalize_ending(context, accusation, public_context, "failure_insufficient_evidence")

    def _finalize_ending(
        self,
        context: ActionExecutionContext,
        accusation: dict,
        public_context: dict,
        ending_type: str,
    ) -> dict:
        context.session.ending_type = ending_type
        context.session.status = "ended"
        context.session.accusation_state = "resolved"
        accusation["state"] = context.session.accusation_state
        ending = {
            "ending_type": ending_type,
            "session_status": context.session.status,
        }
        return {
            "accusation": accusation,
            "public_context": public_context,
            "ending": ending,
        }

    def _has_required_evidence(self, action: ActionRequest, context: ActionExecutionContext, truth: dict) -> bool:
        requested_keys = set(action.payload.get("evidence_clue_keys") or [])
        if not requested_keys:
            return False
        held_keys = {
            clue.key
            for clue in context.clues
            if clue.current_holder_character_id == context.player.character.id
        }
        required_keys = set(truth.get("required_clue_keys") or [])
        return required_keys.issubset(requested_keys & held_keys)

    @staticmethod
    def _player_flag_enabled(context: ActionExecutionContext, flag_name: str) -> bool:
        if context.player.state is None:
            return False
        return bool(context.player.state.status_flags.get(flag_name))

    def _resolve_public_context(self, context: ActionExecutionContext) -> dict:
        current_location = context.player.character.current_location
        if current_location is None:
            return {
                "is_public": False,
                "source": None,
                "event_key": None,
                "location_key": None,
                "participant_keys": [],
            }

        active_event = self._find_active_public_event(context)
        if active_event is None:
            return {
                "is_public": False,
                "source": None,
                "event_key": None,
                "location_key": current_location.key,
                "participant_keys": [],
            }

        event_key = active_event.rule_flags.get("public_context_key") or f"public-{active_event.id}"
        return {
            "is_public": True,
            "source": active_event.rule_flags.get("source") or "scheduled_event",
            "event_key": event_key,
            "location_key": current_location.key,
            "participant_keys": self._participant_keys(active_event, context),
        }

    def _find_active_public_event(self, context: ActionExecutionContext) -> EventModel | None:
        current_location = context.player.character.current_location
        if current_location is None:
            return None
        current_minute = context.session.current_time_minute
        for event in context.events:
            event_location_matches = event.location_id == current_location.id or (
                event.location is not None and event.location.key == current_location.key
            )
            if not event.is_public_event or not event_location_matches:
                continue
            if event.event_state == "ended":
                continue
            if event.start_minute <= current_minute <= event.end_minute:
                return event
        return None

    @staticmethod
    def _participant_keys(event: EventModel, context: ActionExecutionContext) -> list[str]:
        npc_keys_by_character_id = {
            str(npc.character_id): npc.template_key
            for npc in context.npcs
        }
        participant_keys: list[str] = []
        for participant in event.participants:
            if participant.character.kind == "player":
                participant_keys.append("player")
                continue
            npc_key = npc_keys_by_character_id.get(str(participant.character_id))
            if npc_key is not None:
                participant_keys.append(npc_key)
        return participant_keys
