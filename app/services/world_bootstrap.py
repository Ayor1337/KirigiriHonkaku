"""世界状态 bootstrap 服务。"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.ai.game_generation import GameGenerationRuntime, ProgressCallback
from app.models.character import (
    CharacterModel,
    DetectiveBoardModel,
    KnowledgeEntryModel,
    NpcModel,
    NpcScheduleModel,
    NpcStateModel,
    PlayerInventoryModel,
    PlayerKnowledgeModel,
    PlayerModel,
    PlayerStateModel,
    ScheduleEntryModel,
)
from app.models.clue import ClueModel
from app.models.event import EventModel, EventParticipantModel
from app.models.map import ConnectionModel, LocationModel, MapModel
from app.schemas.world_generation import WorldBlueprint


class SessionNotFoundError(RuntimeError):
    """目标会话不存在。"""


class SessionAlreadyBootstrappedError(RuntimeError):
    """目标会话已经完成世界初始化。"""


class SessionGenerationInProgressError(RuntimeError):
    """目标会话正在生成世界。"""


@dataclass
class DraftSessionResult:
    """创建空白会话后的结构化结果。"""

    session_id: str
    session_uuid: str
    directories: dict[str, str]


@dataclass
class BootstrapResult:
    """bootstrap 的结构化返回值。"""

    session_id: str
    status: str
    created_counts: dict[str, int]
    root_ids: dict[str, str]


class WorldBootstrapService:
    """通过多轮 AGENT 生成并装配完整游戏世界。"""

    def __init__(self, uow_factory, generation_runtime: GameGenerationRuntime):
        self._uow_factory = uow_factory
        self._generation_runtime = generation_runtime

    def create_draft_session(self, progress_callback: ProgressCallback = None) -> DraftSessionResult:
        self._emit_progress(progress_callback, "session_creating")
        with self._uow_factory() as uow:
            session = uow.sessions.create()
            uow.commit()
            result = DraftSessionResult(
                session_id=str(session.id),
                session_uuid=session.uuid,
                directories={},
            )
        self._emit_progress(progress_callback, "session_created", {"session_id": result.session_id})
        return result

    def create_and_bootstrap(self, progress_callback: ProgressCallback = None) -> BootstrapResult:
        created = self.create_draft_session(progress_callback=progress_callback)
        return self.bootstrap(created.session_id, progress_callback=progress_callback)

    def bootstrap(self, session_id: str, progress_callback: ProgressCallback = None) -> BootstrapResult:
        session_uuid = self._mark_generating(session_id)
        try:
            blueprint = self._generation_runtime.generate(
                session_uuid=session_uuid,
                progress_callback=progress_callback,
            )
            with self._uow_factory() as uow:
                session = uow.sessions.get(session_id)
                if session is None:
                    raise SessionNotFoundError(session_id)
                if session.status != "generating":
                    raise SessionGenerationInProgressError(session_id)
                if uow.session is None:
                    raise RuntimeError("UnitOfWork session has not been opened.")
                self._emit_progress(progress_callback, "world_persisting", {"session_id": session_id})
                result = self._persist_generated_world(session, blueprint, uow.session)
                uow.commit()
                self._emit_progress(progress_callback, "world_ready", {"session_id": session_id})
                return result
        except Exception:
            self._restore_draft(session_id, session_uuid)
            raise

    def _mark_generating(self, session_id: str) -> str:
        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            if session.status == "generating":
                raise SessionGenerationInProgressError(session_id)
            if session.status != "draft":
                raise SessionAlreadyBootstrappedError(session_id)
            session.status = "generating"
            uow.commit()
            return session.uuid

    def _restore_draft(self, session_id: str, session_uuid: str) -> None:
        self._reset_generated_files(session_uuid)
        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None or session.status != "generating":
                return
            session.status = "draft"
            session.title = None
            session.truth_payload = {}
            uow.commit()

    def _reset_generated_files(self, session_uuid: str) -> None:
        return None

    def _persist_generated_world(self, session, blueprint: WorldBlueprint, db_session) -> BootstrapResult:
        game_map = MapModel(
            session=session,
            template_key=blueprint.map.template_key,
            display_name=blueprint.map.display_name,
        )
        db_session.add(game_map)

        locations_by_key: dict[str, LocationModel] = {}
        for location_seed in blueprint.locations:
            location = LocationModel(
                map=game_map,
                key=location_seed.key,
                name=location_seed.name,
                description=location_seed.description,
                location_type=location_seed.location_type,
                visibility_level=location_seed.visibility_level,
                is_hidden=location_seed.is_hidden,
                status_flags=dict(location_seed.status_flags),
            )
            db_session.add(location)
            locations_by_key[location_seed.key] = location

        for location_seed in blueprint.locations:
            if location_seed.parent_key:
                locations_by_key[location_seed.key].parent = locations_by_key[location_seed.parent_key]

        for connection_seed in blueprint.connections:
            db_session.add(
                ConnectionModel(
                    map=game_map,
                    from_location=locations_by_key[connection_seed.from_location_key],
                    to_location=locations_by_key[connection_seed.to_location_key],
                    connection_type=connection_seed.connection_type,
                    access_rule=dict(connection_seed.access_rule),
                    is_hidden=connection_seed.is_hidden,
                    is_locked=connection_seed.is_locked,
                    is_one_way=connection_seed.is_one_way,
                    is_dangerous=connection_seed.is_dangerous,
                    time_window_rule=dict(connection_seed.time_window_rule),
                )
            )

        player_seed = blueprint.player
        start_location = locations_by_key[player_seed.start_location_key]
        player_character = CharacterModel(
            session=session,
            kind="player",
            display_name=player_seed.display_name,
            public_identity=player_seed.public_identity,
            current_location=start_location,
        )
        player = PlayerModel(
            session=session,
            character=player_character,
            template_key=player_seed.template_key,
            template_name=player_seed.template_name,
            trait_text=player_seed.trait_text,
            background_text=player_seed.background_text,
        )
        player.state = PlayerStateModel(
            hp_state="healthy",
            injury_state="none",
            poison_state="none",
            exposure_value=session.exposure_value,
            exposure_level=session.exposure_level,
            status_flags=dict(player_seed.status_flags),
            temporary_effects={},
            unlocked_access=list(player_seed.unlocked_access),
        )
        player.inventory = PlayerInventoryModel(
            money_amount=0,
            resource_flags={},
            held_item_refs=[],
            equipped_item_refs=[],
            credential_refs=[],
            weapon_refs=[],
            document_refs=[],
        )
        player.knowledge = PlayerKnowledgeModel(summary_text="Initial world state loaded.")
        player.knowledge.entries.append(
            KnowledgeEntryModel(
                source_type="session_bootstrap",
                title="案件开场",
                content=f"玩家已进入案件《{blueprint.title}》的现场，并掌握初始世界状态。",
                importance_level="medium",
                learned_at_minute=0,
            )
        )
        player.detective_board = DetectiveBoardModel(board_layout_version=1)
        db_session.add(player)

        characters_by_key = {"player": player_character}
        npc_models: list[NpcModel] = []
        for npc_seed in blueprint.npcs:
            npc_character = CharacterModel(
                session=session,
                kind="npc",
                display_name=npc_seed.display_name,
                public_identity=npc_seed.public_identity,
                current_location=locations_by_key[npc_seed.location_key],
            )
            npc = NpcModel(
                session=session,
                character=npc_character,
                template_key=npc_seed.key,
                role_type=npc_seed.role_type,
                profile_markdown=npc_seed.profile_markdown,
                memory_markdown=npc_seed.memory_markdown,
            )
            npc.state = NpcStateModel(
                current_location=locations_by_key[npc_seed.location_key],
                attitude_to_player=npc_seed.attitude_to_player,
                alertness_level=npc_seed.alertness_level,
                emotion_tag=npc_seed.emotion_tag,
                has_met_player=False,
                is_available=True,
                is_in_event=False,
                is_under_pressure=False,
                state_flags={},
            )
            npc.schedule = NpcScheduleModel(schedule_mode=npc_seed.schedule_mode)
            for entry_seed in npc_seed.schedule_entries:
                npc.schedule.entries.append(
                    ScheduleEntryModel(
                        start_minute=entry_seed.start_minute,
                        end_minute=entry_seed.end_minute,
                        behavior_type=entry_seed.behavior_type,
                        behavior_description=entry_seed.behavior_description,
                        target_location=locations_by_key[entry_seed.target_location_key],
                        priority=entry_seed.priority,
                    )
                )
            db_session.add(npc)
            npc_models.append(npc)
            characters_by_key[npc_seed.key] = npc_character

        clue_models: list[ClueModel] = []
        for clue_seed in blueprint.clues:
            clue = ClueModel(
                session=session,
                key=clue_seed.key,
                name=clue_seed.name,
                description=clue_seed.description,
                clue_type=clue_seed.clue_type,
                initial_location=locations_by_key[clue_seed.initial_location_key]
                if clue_seed.initial_location_key
                else None,
                initial_holder_character=characters_by_key[clue_seed.initial_holder_character_key]
                if clue_seed.initial_holder_character_key
                else None,
                current_location=locations_by_key[clue_seed.current_location_key]
                if clue_seed.current_location_key
                else None,
                current_holder_character=characters_by_key[clue_seed.current_holder_character_key]
                if clue_seed.current_holder_character_key
                else None,
                is_key_clue=clue_seed.is_key_clue,
                is_movable=clue_seed.is_movable,
                is_time_sensitive=clue_seed.is_time_sensitive,
                clue_state=clue_seed.clue_state,
                discovery_rule=dict(clue_seed.discovery_rule),
                document_markdown=clue_seed.document_markdown,
            )
            db_session.add(clue)
            clue_models.append(clue)

        event_models: list[EventModel] = []
        for event_seed in blueprint.events:
            event = EventModel(
                session=session,
                name=event_seed.name,
                event_type=event_seed.event_type,
                description=event_seed.description,
                location=locations_by_key[event_seed.location_key],
                start_minute=event_seed.start_minute,
                end_minute=event_seed.end_minute,
                event_state=event_seed.event_state,
                is_public_event=event_seed.is_public_event,
                rule_flags=dict(event_seed.rule_flags),
            )
            for participant_seed in event_seed.participants:
                event.participants.append(
                    EventParticipantModel(
                        character=characters_by_key[participant_seed.character_key],
                        participant_role=participant_seed.participant_role,
                        attendance_state=participant_seed.attendance_state,
                    )
                )
            db_session.add(event)
            event_models.append(event)

        session.title = blueprint.title
        session.truth_payload = blueprint.truth.model_dump()
        session.story_markdown = self._render_story_markdown(
            blueprint=blueprint,
            start_location=start_location,
            player=player,
        )
        session.truth_markdown = self._render_truth_markdown(session.truth_payload)
        session.status = "ready"
        db_session.flush()

        return BootstrapResult(
            session_id=str(session.id),
            status=session.status,
            created_counts={
                "characters": 1 + len(npc_models),
                "players": 1,
                "npcs": len(npc_models),
                "locations": len(locations_by_key),
                "connections": len(blueprint.connections),
                "clues": len(clue_models),
                "events": len(event_models),
                "dialogues": 0,
            },
            root_ids={
                "player_id": str(player.id),
                "map_id": str(game_map.id),
            },
        )

    @staticmethod
    def _emit_progress(
        progress_callback: Callable[[str, dict[str, Any]], None] | None,
        placeholder: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(placeholder, payload or {})

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def _render_story_markdown(*, blueprint: WorldBlueprint, start_location: LocationModel, player: PlayerModel) -> str:
        """基于现有世界蓝图渲染玩家开局时看到的 STORY.md。"""

        background = player.background_text or player.character.public_identity or "你受邀来到此地"
        location_description = start_location.description or f"这里是 {start_location.name}。"

        visible_event = next((event for event in blueprint.events if event.is_public_event and event.description), None)
        visible_clue = next(
            (
                clue
                for clue in blueprint.clues
                if clue.current_location_key == start_location.key and clue.description
            ),
            None,
        )

        if visible_event is not None:
            hook_text = f"你刚站稳脚步，就意识到这里并不只是表面上的平静。{visible_event.description}"
        elif visible_clue is not None:
            hook_text = f"在你视线可及的范围里，已经有异样先一步浮了出来：{visible_clue.description}"
        else:
            hook_text = "空气里有一种难以言明的紧绷感，仿佛每个人都在回避真正重要的那句话。"

        return (
            f"# {blueprint.title}\n\n"
            f"你来到 {blueprint.map.display_name} 的 {start_location.name}。{background}。{location_description}\n\n"
            f"{hook_text} 你知道自己此刻看到的还只是案件最外层的轮廓，真正关键的部分，仍藏在人、地点与时间的细缝里。\n\n"
            f"现在，你能依靠的只有自己的观察、判断与发问。先从眼前的现场开始，决定下一步该去哪里、该接触谁、该把哪一处异常当成突破口。\n"
        )

    @staticmethod
    def _render_truth_markdown(truth_payload: dict) -> str:
        return (
            "# Truth\n\n"
            f"- culprit_npc_key: {truth_payload.get('culprit_npc_key')}\n"
            f"- required_clue_keys: {json.dumps(truth_payload.get('required_clue_keys', []), ensure_ascii=False)}\n"
            f"- supporting_clue_keys: {json.dumps(truth_payload.get('supporting_clue_keys', []), ensure_ascii=False)}\n"
            f"- false_verdict_targets: {json.dumps(truth_payload.get('false_verdict_targets', []), ensure_ascii=False)}\n"
            f"- countermeasure_plan: {json.dumps(truth_payload.get('countermeasure_plan', {}), ensure_ascii=False)}\n"
        )
