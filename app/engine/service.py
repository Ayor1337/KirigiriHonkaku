"""Game Engine 主流程。"""

from dataclasses import dataclass
from typing import Any

from app.engine.rules import AccusationRule, ClueRule, ExposureRule, MapRule, NpcScheduleRule, TimeRule
from app.engine.rules.base import ActionExecutionContext
from app.models.dialogue import DialogueModel, DialogueParticipantModel
from app.models.map import ConnectionModel, LocationModel
from app.models.session import SessionModel
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.schemas.action import ActionRequest, AiTask, SceneSnapshot


@dataclass
class EngineResult:
    """封装引擎对一次 Action 的结构化结算结果。"""

    status: str
    state_delta_summary: dict
    scene_snapshot: SceneSnapshot
    ai_tasks: list[AiTask]
    errors: list[str]


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

    def process(self, action: ActionRequest, session: SessionModel, uow: SqlAlchemyUnitOfWork) -> EngineResult:
        """按固定顺序处理 Action，并产出结构化结果。"""

        player = uow.players.get_by_session(action.session_id)
        game_map = uow.maps.get_by_session(action.session_id)
        if player is None or game_map is None:
            raise RuntimeError("Session world state is incomplete.")

        context = ActionExecutionContext(
            session=session,
            player=player,
            npcs=uow.npcs.list_by_session(action.session_id),
            game_map=game_map,
            clues=uow.clues.list_by_session(action.session_id),
            dialogues=uow.dialogues.list_by_session(action.session_id),
            previous_time_minute=session.current_time_minute,
        )
        self._prevalidate(action, context)

        module_outputs: dict[str, Any] = {}
        if context.accepted:
            for module in self.modules:
                module_outputs[module.name] = module.apply(action, context)
        else:
            module_outputs = {}

        dialogue_summary = None
        if context.accepted and action.action_type == "talk":
            dialogue_summary = self._create_dialogue(context, uow)

        latest_dialogue = dialogue_summary or self._get_latest_dialogue_summary(context)
        scene_snapshot = SceneSnapshot(
            session_id=str(session.id),
            actor_id=action.actor_id,
            current_time_minute=session.current_time_minute,
            details=self._build_scene_details(context, latest_dialogue),
        )
        state_delta_summary = {
            "hard_state_updated": context.accepted,
            "current_time_minute": session.current_time_minute,
            "accusation_state": session.accusation_state,
            "module_outputs": module_outputs,
            "movement": module_outputs.get("map", {}).get("movement"),
            "investigation": module_outputs.get("clue", {}).get(
                "investigation",
                {"discovered_clues": []},
            ),
            "dialogue": dialogue_summary,
        }
        ai_tasks = [
            AiTask(
                task_name=f"{action.action_type}_{'narration' if context.accepted else 'rejection'}",
                context={
                    "session_id": str(session.id),
                    "current_time_minute": session.current_time_minute,
                    "status": "accepted" if context.accepted else "rejected",
                },
            )
        ]
        return EngineResult(
            status="accepted" if context.accepted else "rejected",
            state_delta_summary=state_delta_summary,
            scene_snapshot=scene_snapshot,
            ai_tasks=ai_tasks,
            errors=context.errors,
        )

    def _prevalidate(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        if action.action_type == "move":
            self._resolve_move_target(action, context)
        elif action.action_type == "talk":
            self._resolve_talk_target(action, context)

    def _resolve_move_target(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return

        target_key = action.payload.get("target_location_key")
        if not isinstance(target_key, str) or not target_key:
            context.reject("Target location key is required.")
            return

        locations_by_key = {location.key: location for location in context.game_map.locations}
        target_location = locations_by_key.get(target_key)
        if target_location is None:
            context.reject("Target location does not exist.")
            return
        if target_location.id == current_location.id:
            context.reject("Target location is already current location.")
            return
        if not self._is_reachable(current_location.id, target_location.id, context.game_map.connections):
            context.reject("Target location is not reachable from current location.")
            return

        context.resolved_target_location = target_location

    def _resolve_talk_target(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return

        target_npc_key = action.payload.get("target_npc_key")
        if not isinstance(target_npc_key, str) or not target_npc_key:
            context.reject("Target NPC key is required.")
            return

        target_npc = next((npc for npc in context.npcs if npc.template_key == target_npc_key), None)
        if target_npc is None:
            context.reject("Target NPC does not exist.")
            return

        if (
            target_npc.state is None
            or target_npc.state.current_location_id != current_location.id
            or not target_npc.state.is_available
            or not target_npc.character.can_participate_dialogue
        ):
            context.reject("Target NPC is not available in the current location.")
            return

        context.resolved_target_npc = target_npc

    @staticmethod
    def _is_reachable(current_location_id: str, target_location_id: str, connections: list[ConnectionModel]) -> bool:
        for connection in connections:
            if connection.is_hidden or connection.is_locked:
                continue
            if connection.from_location_id == current_location_id and connection.to_location_id == target_location_id:
                return True
            if not connection.is_one_way and connection.from_location_id == target_location_id and connection.to_location_id == current_location_id:
                return True
        return False

    def _reachable_locations(self, current_location: LocationModel, connections: list[ConnectionModel]) -> list[LocationModel]:
        reachable: dict[str, LocationModel] = {}
        for connection in connections:
            if connection.is_hidden or connection.is_locked:
                continue
            if connection.from_location_id == current_location.id:
                reachable[connection.to_location_id] = connection.to_location
            elif not connection.is_one_way and connection.to_location_id == current_location.id:
                reachable[connection.from_location_id] = connection.from_location
        return sorted(reachable.values(), key=lambda location: location.key)

    def _create_dialogue(self, context: ActionExecutionContext, uow: SqlAlchemyUnitOfWork) -> dict[str, Any]:
        current_location = context.player.character.current_location
        target_npc = context.resolved_target_npc
        if current_location is None or target_npc is None:
            raise RuntimeError("Dialogue target was not resolved.")

        dialogue = DialogueModel(
            session=context.session,
            dialogue_type="conversation",
            location=current_location,
            start_minute=context.previous_time_minute,
            end_minute=context.session.current_time_minute,
            tag_flags={},
        )
        dialogue.participants.append(
            DialogueParticipantModel(
                character=context.player.character,
                participant_role="player",
            )
        )
        dialogue.participants.append(
            DialogueParticipantModel(
                character=target_npc.character,
                participant_role="npc",
            )
        )
        if uow.session is None:
            raise RuntimeError("UnitOfWork session has not been opened.")
        uow.session.add(dialogue)
        uow.session.flush()
        context.dialogues.append(dialogue)
        context.created_dialogue = dialogue
        return {
            "dialogue_id": str(dialogue.id),
            "target_npc_key": target_npc.template_key,
            "location_key": current_location.key,
            "start_minute": dialogue.start_minute,
            "end_minute": dialogue.end_minute,
            "participant_keys": ["player", target_npc.template_key],
        }

    def _get_latest_dialogue_summary(self, context: ActionExecutionContext) -> dict[str, Any] | None:
        if not context.dialogues:
            return None

        latest = max(
            context.dialogues,
            key=lambda dialogue: (dialogue.start_minute, dialogue.created_at),
        )
        npc_keys_by_character_id = {
            str(npc.character_id): npc.template_key
            for npc in context.npcs
        }
        participant_keys = []
        target_npc_key = None
        for participant in latest.participants:
            character = participant.character
            if character.kind == "player":
                participant_keys.append("player")
                continue
            npc_key = npc_keys_by_character_id.get(str(character.id))
            if npc_key is not None:
                participant_keys.append(npc_key)
                target_npc_key = npc_key

        return {
            "dialogue_id": str(latest.id),
            "target_npc_key": target_npc_key,
            "location_key": latest.location.key,
            "start_minute": latest.start_minute,
            "end_minute": latest.end_minute,
            "participant_keys": participant_keys,
        }

    def _build_scene_details(
        self,
        context: ActionExecutionContext,
        latest_dialogue: dict[str, Any] | None,
    ) -> dict[str, Any]:
        current_location = context.player.character.current_location
        if current_location is None:
            return {
                "current_location": None,
                "reachable_locations": [],
                "visible_npcs": [],
                "investigable_clues": [],
                "latest_dialogue": latest_dialogue,
            }

        reachable_locations = [
            {
                "key": location.key,
                "name": location.name,
            }
            for location in self._reachable_locations(current_location, context.game_map.connections)
        ]
        visible_npcs = [
            {
                "key": npc.template_key,
                "display_name": npc.character.display_name,
            }
            for npc in sorted(context.npcs, key=lambda item: item.template_key or "")
            if npc.state is not None and npc.state.current_location_id == current_location.id and npc.state.is_available
        ]
        investigable_clues = [
            {
                "key": clue.key,
                "name": clue.name,
                "clue_type": clue.clue_type,
            }
            for clue in sorted(context.clues, key=lambda item: item.key)
            if clue.current_location_id == current_location.id and clue.is_movable
        ]
        return {
            "current_location": {
                "key": current_location.key,
                "name": current_location.name,
                "description": current_location.description,
            },
            "reachable_locations": reachable_locations,
            "visible_npcs": visible_npcs,
            "investigable_clues": investigable_clues,
            "latest_dialogue": latest_dialogue,
        }

