"""世界状态 bootstrap 服务。"""

import re
from dataclasses import dataclass

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
from app.seeds.world import DefaultWorldSeedProvider


class SessionNotFoundError(RuntimeError):
    """目标会话不存在。"""


class SessionAlreadyBootstrappedError(RuntimeError):
    """目标会话已经完成世界初始化。"""


@dataclass
class BootstrapResult:
    """bootstrap 的结构化返回值。"""

    session_id: str
    status: str
    created_counts: dict[str, int]
    root_ids: dict[str, str]


class WorldBootstrapService:
    """将会话模板 key 装配为最小世界状态。"""

    def __init__(self, uow_factory, file_storage, seed_provider: DefaultWorldSeedProvider | None = None):
        self._uow_factory = uow_factory
        self._file_storage = file_storage
        self._seed_provider = seed_provider or DefaultWorldSeedProvider()

    def bootstrap(self, session_id: str) -> BootstrapResult:
        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            if session.status == "ready":
                raise SessionAlreadyBootstrappedError(session_id)
            if uow.session is None:
                raise RuntimeError("UnitOfWork session has not been opened.")

            seed = self._seed_provider.resolve(session)
            self._file_storage.create_session_tree(session.uuid)
            db_session = uow.session

            game_map = MapModel(
                session=session,
                template_key=seed["map"].get("template_key") or session.map_template_key,
                display_name=seed["map"]["display_name"],
            )
            db_session.add(game_map)

            locations_by_key: dict[str, LocationModel] = {}
            for location_seed in seed["locations"]:
                location = LocationModel(
                    map=game_map,
                    name=location_seed["name"],
                    description=location_seed.get("description"),
                    location_type=location_seed["location_type"],
                    visibility_level=location_seed.get("visibility_level"),
                    is_hidden=location_seed.get("is_hidden", False),
                    status_flags=dict(location_seed.get("status_flags", {})),
                )
                db_session.add(location)
                locations_by_key[location_seed["key"]] = location

            for location_seed in seed["locations"]:
                parent_key = location_seed.get("parent_key")
                if parent_key:
                    locations_by_key[location_seed["key"]].parent = locations_by_key[parent_key]

            for connection_seed in seed["connections"]:
                db_session.add(
                    ConnectionModel(
                        map=game_map,
                        from_location=locations_by_key[connection_seed["from_location_key"]],
                        to_location=locations_by_key[connection_seed["to_location_key"]],
                        connection_type=connection_seed.get("connection_type"),
                        access_rule=dict(connection_seed.get("access_rule", {})),
                        is_hidden=connection_seed.get("is_hidden", False),
                        is_locked=connection_seed.get("is_locked", False),
                        is_one_way=connection_seed.get("is_one_way", False),
                        is_dangerous=connection_seed.get("is_dangerous", False),
                        time_window_rule=dict(connection_seed.get("time_window_rule", {})),
                    )
                )

            player_seed = seed["player"]
            player_character = CharacterModel(
                session=session,
                kind="player",
                display_name=player_seed["display_name"],
                public_identity=player_seed.get("public_identity"),
                current_location=locations_by_key[player_seed["start_location_key"]],
            )
            player = PlayerModel(
                session=session,
                character=player_character,
                template_key=player_seed.get("template_key") or session.case_template_key,
                template_name=player_seed.get("template_name"),
                trait_text=player_seed.get("trait_text"),
                background_text=player_seed.get("background_text"),
            )
            player.state = PlayerStateModel(
                hp_state="healthy",
                injury_state="none",
                poison_state="none",
                exposure_value=session.exposure_value,
                exposure_level=session.exposure_level,
                status_flags={},
                temporary_effects={},
                unlocked_access=list(player_seed.get("unlocked_access", [])),
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
                    content="玩家已进入案件现场，并掌握初始世界状态。",
                    importance_level="medium",
                    learned_at_minute=0,
                )
            )
            player.detective_board = DetectiveBoardModel(board_layout_version=1)
            db_session.add(player)

            characters_by_key = {"player": player_character}
            npc_models: list[NpcModel] = []
            for npc_seed in seed["npcs"]:
                npc_character = CharacterModel(
                    session=session,
                    kind="npc",
                    display_name=npc_seed["display_name"],
                    public_identity=npc_seed.get("public_identity"),
                    current_location=locations_by_key[npc_seed["location_key"]],
                )
                slug = self._slugify(npc_seed["key"])
                npc = NpcModel(
                    session=session,
                    character=npc_character,
                    template_key=npc_seed["key"],
                    role_type=npc_seed.get("role_type"),
                    profile_file_path=self._file_storage.write_session_file(
                        session.uuid,
                        "npc",
                        f"{slug}_PROFILE.md",
                        npc_seed.get("profile_markdown", ""),
                    ),
                    memory_file_path=self._file_storage.write_session_file(
                        session.uuid,
                        "npc",
                        f"{slug}_MEMORY.md",
                        npc_seed.get("memory_markdown", ""),
                    ),
                )
                npc.state = NpcStateModel(
                    current_location=locations_by_key[npc_seed["location_key"]],
                    attitude_to_player=npc_seed.get("attitude_to_player"),
                    alertness_level=npc_seed.get("alertness_level"),
                    emotion_tag=npc_seed.get("emotion_tag"),
                    is_available=True,
                    is_in_event=False,
                    is_under_pressure=False,
                    state_flags={},
                )
                npc.schedule = NpcScheduleModel(schedule_mode=npc_seed.get("schedule_mode"))
                for entry_seed in npc_seed.get("schedule_entries", []):
                    npc.schedule.entries.append(
                        ScheduleEntryModel(
                            start_minute=entry_seed["start_minute"],
                            end_minute=entry_seed["end_minute"],
                            behavior_type=entry_seed["behavior_type"],
                            behavior_description=entry_seed.get("behavior_description"),
                            target_location=locations_by_key[entry_seed["target_location_key"]],
                            priority=entry_seed.get("priority", 0),
                        )
                    )
                db_session.add(npc)
                npc_models.append(npc)
                characters_by_key[npc_seed["key"]] = npc_character

            clue_models: list[ClueModel] = []
            for clue_seed in seed["clues"]:
                clue = ClueModel(
                    session=session,
                    name=clue_seed["name"],
                    description=clue_seed.get("description"),
                    clue_type=clue_seed["clue_type"],
                    initial_location=locations_by_key[clue_seed["initial_location_key"]]
                    if clue_seed.get("initial_location_key")
                    else None,
                    initial_holder_character=characters_by_key[clue_seed["initial_holder_character_key"]]
                    if clue_seed.get("initial_holder_character_key")
                    else None,
                    current_location=locations_by_key[clue_seed["current_location_key"]]
                    if clue_seed.get("current_location_key")
                    else None,
                    current_holder_character=characters_by_key[clue_seed["current_holder_character_key"]]
                    if clue_seed.get("current_holder_character_key")
                    else None,
                    is_key_clue=clue_seed.get("is_key_clue", False),
                    is_movable=clue_seed.get("is_movable", True),
                    is_time_sensitive=clue_seed.get("is_time_sensitive", False),
                    clue_state=clue_seed.get("clue_state", "hidden"),
                    document_file_path=self._file_storage.write_session_file(
                        session.uuid,
                        "clue",
                        f"{self._slugify(clue_seed['name'])}.md",
                        clue_seed.get("document_markdown", ""),
                    ),
                )
                db_session.add(clue)
                clue_models.append(clue)

            event_models: list[EventModel] = []
            for event_seed in seed["events"]:
                event = EventModel(
                    session=session,
                    name=event_seed["name"],
                    event_type=event_seed["event_type"],
                    description=event_seed.get("description"),
                    location=locations_by_key[event_seed["location_key"]],
                    start_minute=event_seed["start_minute"],
                    end_minute=event_seed["end_minute"],
                    event_state=event_seed.get("event_state", "scheduled"),
                    is_public_event=event_seed.get("is_public_event", False),
                    rule_flags=dict(event_seed.get("rule_flags", {})),
                )
                for participant_seed in event_seed.get("participants", []):
                    event.participants.append(
                        EventParticipantModel(
                            character=characters_by_key[participant_seed["character_key"]],
                            participant_role=participant_seed.get("participant_role"),
                            attendance_state=participant_seed.get("attendance_state"),
                        )
                    )
                db_session.add(event)
                event_models.append(event)

            session.status = "ready"
            db_session.flush()
            uow.commit()

            return BootstrapResult(
                session_id=str(session.id),
                status=session.status,
                created_counts={
                    "characters": 1 + len(npc_models),
                    "players": 1,
                    "npcs": len(npc_models),
                    "locations": len(locations_by_key),
                    "connections": len(seed["connections"]),
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
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
