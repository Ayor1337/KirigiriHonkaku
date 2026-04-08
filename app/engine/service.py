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
        """按固定顺序注册规则模块，保证动作结算语义稳定。"""

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
            events=uow.events.list_by_session(action.session_id),
            dialogues=uow.dialogues.list_by_session(action.session_id),
            previous_time_minute=session.current_time_minute,
        )
        # 预校验阶段只负责解析目标和拒绝非法动作，不直接改动硬状态。
        self._prevalidate(action, context)

        module_outputs: dict[str, Any] = {}
        if context.accepted:
            # 所有规则共享同一份 context，前置规则写入的结果会被后置规则消费。
            for module in self.modules:
                module_outputs[module.name] = module.apply(action, context)
        else:
            module_outputs = {}

        dialogue_summary = None
        if context.accepted and action.action_type == "talk":
            dialogue_summary = self._create_dialogue(context, uow)

        latest_dialogue = dialogue_summary or self._get_latest_dialogue_summary(context)
        # 这里统一补齐缺失的派生字段，确保即使某个规则未触发也能返回完整快照。
        public_context = module_outputs.get("accusation", {}).get("public_context") or self._describe_public_context(context)
        exposure = module_outputs.get("exposure", {}).get("exposure") or {
            "previous_value": context.session.exposure_value,
            "value": context.session.exposure_value,
            "delta": 0,
            "previous_level": context.session.exposure_level,
            "level": context.session.exposure_level,
        }
        risk = module_outputs.get("exposure", {}).get("risk") or {
            "countermeasure_triggered": False,
            "mode": None,
            "affected_npc_keys": [],
        }
        accusation = module_outputs.get("accusation", {}).get("accusation") or {
            "state": context.session.accusation_state,
            "resolution": None,
            "requested_context_mode": None,
            "resolved_context_mode": "public" if public_context["is_public"] else "private",
            "target_npc_key": getattr(context.resolved_target_npc, "template_key", None),
        }
        ending = module_outputs.get("accusation", {}).get("ending") or {
            "ending_type": context.session.ending_type,
            "session_status": context.session.status,
        }

        scene_snapshot = SceneSnapshot(
            session_id=str(session.id),
            actor_id=action.actor_id,
            current_time_minute=session.current_time_minute,
            details=self._build_scene_details(context, latest_dialogue, public_context, exposure, risk),
        )
        state_delta_summary = {
            "hard_state_updated": context.accepted,
            "current_time_minute": session.current_time_minute,
            "accusation_state": session.accusation_state,
            "ending_type": session.ending_type,
            "module_outputs": module_outputs,
            "movement": module_outputs.get("map", {}).get("movement"),
            "investigation": module_outputs.get("clue", {}).get(
                "investigation",
                {"discovered_clues": [], "granted_access_tokens": []},
            ),
            "dialogue": dialogue_summary,
            "exposure": exposure,
            "risk": risk,
            "public_context": public_context,
            "accusation": accusation,
            "ending": ending,
        }
        ai_tasks = [
            AiTask(
                task_name=f"{action.action_type}_{'narration' if context.accepted else 'rejection'}",
                context={
                    "session_id": str(session.id),
                    "current_time_minute": session.current_time_minute,
                    "status": "accepted" if context.accepted else "rejected",
                    "ending_type": session.ending_type,
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
        """在规则链运行前解析动作目标，并尽早拒绝无效输入。"""

        if action.action_type == "move":
            self._resolve_move_target(action, context)
        elif action.action_type == "talk":
            self._resolve_talk_target(action, context)
        elif action.action_type == "gather":
            self._resolve_gather_location(action, context)
        elif action.action_type == "accuse":
            self._resolve_accuse_target(action, context)

    def _resolve_move_target(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        """校验移动目标是否存在且可达，并写回解析后的地点对象。"""

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

        unlocked_access = []
        if context.player.state is not None:
            unlocked_access = context.player.state.unlocked_access
        if not self._is_reachable(current_location.id, target_location.id, context.game_map.connections, unlocked_access):
            context.reject("Target location is not reachable from current location.")
            return

        context.resolved_target_location = target_location

    def _resolve_talk_target(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        """校验对话文本和 NPC 目标，并确认对方当前可被交互。"""

        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return

        player_text = action.payload.get("text")
        if not isinstance(player_text, str) or not player_text.strip():
            context.reject("Talk text is required.")
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

    def _resolve_gather_location(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        """确保调查动作只针对玩家当前所在地点。"""

        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return

        target_key = action.payload.get("location_key")
        if target_key is None:
            return
        if not isinstance(target_key, str) or target_key != current_location.key:
            context.reject("Gather action must target the current location.")

    def _resolve_accuse_target(self, action: ActionRequest, context: ActionExecutionContext) -> None:
        """校验指认目标，并确认其处于可被当面对质的场景中。"""

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
        ):
            context.reject("Target NPC is not available in the current location.")
            return

        context.resolved_target_npc = target_npc

    @staticmethod
    def _is_reachable(
        current_location_id: str,
        target_location_id: str,
        connections: list[ConnectionModel],
        unlocked_access: list[str],
    ) -> bool:
        """判断两点之间是否存在当前可通行的直接连接。"""

        for connection in connections:
            if not GameEngine._connection_is_accessible(connection, unlocked_access):
                continue
            if connection.from_location_id == current_location_id and connection.to_location_id == target_location_id:
                return True
            if not connection.is_one_way and connection.from_location_id == target_location_id and connection.to_location_id == current_location_id:
                return True
        return False

    def _reachable_locations(
        self,
        current_location: LocationModel,
        connections: list[ConnectionModel],
        unlocked_access: list[str],
    ) -> list[LocationModel]:
        """列出当前位置可直达的地点，用于场景快照展示。"""

        reachable: dict[str, LocationModel] = {}
        for connection in connections:
            if not self._connection_is_accessible(connection, unlocked_access):
                continue
            if connection.from_location_id == current_location.id:
                reachable[connection.to_location_id] = connection.to_location
            elif not connection.is_one_way and connection.to_location_id == current_location.id:
                reachable[connection.from_location_id] = connection.from_location
        return sorted(reachable.values(), key=lambda location: location.key)

    @staticmethod
    def _connection_is_accessible(connection: ConnectionModel, unlocked_access: list[str]) -> bool:
        """按显式锁定状态和访问令牌判断连接是否可用。"""

        if connection.is_hidden or connection.is_locked:
            return False
        required_token = connection.access_rule.get("required_token")
        if isinstance(required_token, str) and required_token:
            return required_token in unlocked_access
        return True

    @staticmethod
    def _clue_is_discoverable(clue, current_time_minute: int, unlocked_access: list[str]) -> bool:
        """根据时间窗和访问令牌判断线索此刻是否可被发现。"""

        discovery_rule = clue.discovery_rule or {}
        required_tokens = discovery_rule.get("required_access_tokens", [])
        if required_tokens and not set(required_tokens).issubset(set(unlocked_access)):
            return False
        min_time_minute = discovery_rule.get("min_time_minute")
        if isinstance(min_time_minute, int) and current_time_minute < min_time_minute:
            return False
        return True

    def _create_dialogue(self, context: ActionExecutionContext, uow: SqlAlchemyUnitOfWork) -> dict[str, Any]:
        """创建或复用一条对话聚合，并返回给上层消费的摘要。"""

        current_location = context.player.character.current_location
        target_npc = context.resolved_target_npc
        if current_location is None or target_npc is None:
            raise RuntimeError("Dialogue target was not resolved.")

        if target_npc.state is not None:
            target_npc.state.has_met_player = True

        dialogue = self._find_reusable_dialogue(context, target_npc.character_id, current_location.id)
        if dialogue is None:
            # 同一地点首次与目标 NPC 对话时新建聚合，后续回合则复用以累积发言历史。
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
        else:
            dialogue.end_minute = context.session.current_time_minute

        context.created_dialogue = dialogue
        return {
            "dialogue_id": str(dialogue.id),
            "target_npc_key": target_npc.template_key,
            "location_key": current_location.key,
            "start_minute": dialogue.start_minute,
            "end_minute": dialogue.end_minute,
            "participant_keys": ["player", target_npc.template_key],
        }

    @staticmethod
    def _find_reusable_dialogue(context: ActionExecutionContext, target_character_id: str, current_location_id: str):
        """查找同地点、同参与者的最近一条对话，用于延续历史。"""

        candidate_dialogues = sorted(
            context.dialogues,
            key=lambda dialogue: (dialogue.end_minute or dialogue.start_minute, dialogue.created_at),
            reverse=True,
        )
        for dialogue in candidate_dialogues:
            if dialogue.location_id != current_location_id:
                continue
            participant_ids = {str(participant.character_id) for participant in dialogue.participants}
            if str(context.player.character_id) not in participant_ids:
                continue
            if str(target_character_id) not in participant_ids:
                continue
            return dialogue
        return None

    def _get_latest_dialogue_summary(self, context: ActionExecutionContext) -> dict[str, Any] | None:
        """在当前动作未新建对话时，回退到最近一条对话摘要。"""

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
        public_context: dict[str, Any],
        exposure: dict[str, Any],
        risk: dict[str, Any],
    ) -> dict[str, Any]:
        """组装给叙事层和前端消费的最小场景快照。"""

        current_location = context.player.character.current_location
        unlocked_access = []
        if context.player.state is not None:
            unlocked_access = context.player.state.unlocked_access
        if current_location is None:
            return {
                "current_location": None,
                "reachable_locations": [],
                "visible_npcs": [],
                "investigable_clues": [],
                "latest_dialogue": latest_dialogue,
                "public_context": public_context,
                "risk": risk,
                "exposure": exposure,
            }

        reachable_locations = [
            {
                "key": location.key,
                "name": location.name,
            }
            for location in self._reachable_locations(current_location, context.game_map.connections, unlocked_access)
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
            if clue.current_location_id == current_location.id
            and clue.is_movable
            and self._clue_is_discoverable(clue, context.session.current_time_minute, unlocked_access)
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
            "public_context": public_context,
            "risk": risk,
            "exposure": exposure,
        }

    def _describe_public_context(self, context: ActionExecutionContext) -> dict[str, Any]:
        """推导玩家当前是否处于公共事件语境中。"""

        current_location = context.player.character.current_location
        if current_location is None:
            return {
                "is_public": False,
                "source": None,
                "event_key": None,
                "location_key": None,
                "participant_keys": [],
            }

        current_minute = context.session.current_time_minute
        npc_keys_by_character_id = {str(npc.character_id): npc.template_key for npc in context.npcs}
        for event in context.events:
            if not event.is_public_event or event.location_id != current_location.id:
                continue
            if event.event_state == "ended":
                continue
            if not (event.start_minute <= current_minute <= event.end_minute):
                continue

            participant_keys = []
            for participant in event.participants:
                if participant.character.kind == "player":
                    participant_keys.append("player")
                    continue
                npc_key = npc_keys_by_character_id.get(str(participant.character_id))
                if npc_key is not None:
                    participant_keys.append(npc_key)
            return {
                "is_public": True,
                "source": event.rule_flags.get("source") or "scheduled_event",
                "event_key": event.rule_flags.get("public_context_key") or f"public-{event.id}",
                "location_key": current_location.key,
                "participant_keys": participant_keys,
            }

        return {
            "is_public": False,
            "source": None,
            "event_key": None,
            "location_key": current_location.key,
            "participant_keys": [],
        }
