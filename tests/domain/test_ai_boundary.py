from pathlib import Path
from uuid import uuid4

from app.ai.game_generation import OpenAiGameGenerationRuntime, UnavailableGameGenerationRuntime
from app.ai.runtime import FallbackNarrativeRuntime, OpenAiNarrativeRuntime
from app.core.config import Settings
from app.main import build_container
from app.schemas.action import SoftStatePatch
from app.schemas.world_generation import WorldBlueprint


class _FakeNotFoundError(Exception):
    status_code = 404


class _FakeResponsesApi:
    def create(self, **kwargs):
        raise _FakeNotFoundError("Error code: 404")


class _FakeChatCompletionsApi:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, **kwargs):
        message = type("Message", (), {"content": self._content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.responses = _FakeResponsesApi()
        self.chat = type("ChatApi", (), {"completions": _FakeChatCompletionsApi(content)})()


def test_build_container_uses_fallback_runtime_without_provider_config():
    runtime_root = Path("tests_runtime") / uuid4().hex
    runtime_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{runtime_root / 'test.db'}",
        data_root=runtime_root / "data",
        auto_create_schema=True,
        openai_api_key=None,
        openai_model=None,
    )

    try:
        container = build_container(settings)
        assert container.ai_runtime.__class__.__name__ == "FallbackNarrativeRuntime"
        assert isinstance(container.game_generation_runtime, UnavailableGameGenerationRuntime)
    finally:
        if runtime_root.exists():
            import shutil

            shutil.rmtree(runtime_root, ignore_errors=True)


def test_build_container_uses_dedicated_game_generation_timeout():
    runtime_root = Path("tests_runtime") / uuid4().hex
    runtime_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{runtime_root / 'test.db'}",
        data_root=runtime_root / "data",
        auto_create_schema=True,
        openai_api_key="test-key",
        openai_model="test-model",
        openai_timeout_seconds=11,
        openai_game_generation_timeout_seconds=99,
    )

    try:
        container = build_container(settings)
        assert container.ai_runtime._timeout_seconds == 11
        assert container.game_generation_runtime._timeout_seconds == 99
    finally:
        if runtime_root.exists():
            import shutil

            shutil.rmtree(runtime_root, ignore_errors=True)


def test_soft_state_patch_rejects_hard_state_keys():
    patch = SoftStatePatch.model_validate(
        {
            "allowed": False,
            "npc_updates": {
                "journalist": {
                    "current_time_minute": 120,
                    "attitude_to_player": "guarded",
                    "emotion_tag": "wary",
                }
            },
            "dialogue_updates": {"tag_flags": {"tone": "tense"}},
        }
    )

    assert "journalist.current_time_minute" in patch.rejected_keys
    assert patch.npc_updates == {
        "journalist": {
            "attitude_to_player": "guarded",
            "emotion_tag": "wary",
        }
    }
    assert patch.dialogue_updates == {"tag_flags": {"tone": "tense"}}


def test_game_generation_runtime_falls_back_to_chat_completions_on_404():
    runtime = OpenAiGameGenerationRuntime.__new__(OpenAiGameGenerationRuntime)
    runtime._client = _FakeClient('{"title": "fallback"}')
    runtime._model = "deepseek-chat"
    runtime._timeout_seconds = 30

    assert runtime._request_json("prompt") == {"title": "fallback"}


def test_narrative_runtime_falls_back_to_chat_completions_on_404():
    runtime = OpenAiNarrativeRuntime.__new__(OpenAiNarrativeRuntime)
    runtime._client = _FakeClient('{"narrative_text": "fallback"}')
    runtime._model = "deepseek-chat"
    runtime._timeout_seconds = 30

    assert runtime._request_text("prompt") == '{"narrative_text": "fallback"}'


def test_game_generation_runtime_accepts_fenced_json_output():
    runtime = OpenAiGameGenerationRuntime.__new__(OpenAiGameGenerationRuntime)
    runtime._client = _FakeClient('```json\n{"title": "fallback"}\n```')
    runtime._model = "deepseek-chat"
    runtime._timeout_seconds = 30

    assert runtime._request_json("prompt") == {"title": "fallback"}


def test_narrative_runtime_accepts_fenced_json_output():
    payload = OpenAiNarrativeRuntime._parse_payload(
        '```json\n{"narrative_text": "fallback"}\n```',
        {"action_type": "talk", "target_npc_key": "npc", "target_npc_name": "NPC"},
    )

    assert payload["narrative_text"] == "fallback"


def test_fallback_narrative_runtime_prefers_location_name_over_key():
    runtime = FallbackNarrativeRuntime()
    engine_result = type("EngineResult", (), {"status": "accepted", "errors": []})()

    result = runtime.run(
        engine_result,
        {
            "action_type": "move",
            "location_key": "archive-room",
            "location_name": "档案室",
        },
    )

    assert "档案室" in result.narrative_text
    assert "archive-room" not in result.narrative_text


def test_narrative_prompt_includes_location_name_and_forbids_key_output():
    engine_result = type("EngineResult", (), {"status": "accepted", "errors": []})()

    prompt = OpenAiNarrativeRuntime._build_prompt(
        engine_result,
        {
            "action_type": "talk",
            "location_key": "archive-room",
            "location_name": "档案室",
            "target_npc_key": "journalist",
            "target_npc_name": "记者",
        },
    )

    assert "当前地点名称: 档案室" in prompt
    assert "当前地点标签: archive-room" in prompt
    assert "不得把地点标签直接写进 narrative_text" in prompt


def test_game_generation_runtime_clamps_plan_counts_to_schema_bounds():
    runtime = OpenAiGameGenerationRuntime.__new__(OpenAiGameGenerationRuntime)

    normalized = runtime._normalize_plan_payload(
        {
            "title": "title",
            "premise": "premise",
            "setting": "setting",
            "tone": "tone",
            "target_location_count": 99,
            "target_npc_count": 0,
            "target_clue_count": 12,
            "target_event_count": 9,
        }
    )

    assert normalized["target_location_count"] == 12
    assert normalized["target_npc_count"] == 2
    assert normalized["target_clue_count"] == 8
    assert normalized["target_event_count"] == 4


def test_game_generation_runtime_normalizes_common_blueprint_aliases():
    runtime = OpenAiGameGenerationRuntime.__new__(OpenAiGameGenerationRuntime)
    payload = {
        "title": "Manor Case",
        "map": {"display_name": "Map", "description": "ignored"},
        "locations": [
            {"key": "foyer", "display_name": "Foyer", "atmosphere": "cold", "type": "hall"},
            {"key": "study", "display_name": "Study", "atmosphere": "quiet", "type": "room"},
        ],
        "connections": [
            {"from_key": "foyer", "to_key": "study"},
            {"from_location_key": "study", "to_location_key": "foyer"},
        ],
        "player": {"display_name": "Detective", "start_location_key": "foyer", "profile_markdown": "ignored"},
        "npcs": [
            {
                "key": "butler",
                "display_name": "Butler",
                "location_key": "study",
                "profile_markdown": "profile",
                "memory_markdown": "memory",
            }
        ],
        "clues": [
            {
                "key": "letter",
                "display_name": "Letter",
                "clue_type": "document",
                "initial_holder_key": "butler",
                "current_holder_character_key": "butler",
                "document_markdown": "doc",
            }
        ],
        "events": [
            {
                "key": "alarm",
                "display_name": "Alarm",
                "event_type": "incident",
                "location_key": "foyer",
                "start_minute": 5,
                "end_minute": 10,
                "trigger_condition": "noise",
                "effect_markdown": "alarm rings",
                "participants": [{"npc_key": "butler"}],
            }
        ],
        "truth": {
            "culprit_npc_key": "butler",
            "required_clue_keys": ["letter"],
            "supporting_clue_keys": [],
            "false_verdict_targets": [],
            "public_accusation_event_keys": ["Alarm"],
            "countermeasure_plan": {"indirect": [], "direct": []},
            "private_encounter_rules": {"violent_flag": False, "fabricate_flag": False},
            "method_markdown": "ignored",
        },
    }

    normalized = runtime._normalize_blueprint_payload(payload)
    blueprint = WorldBlueprint.model_validate(normalized)

    assert blueprint.locations[0].name == "Foyer"
    assert blueprint.locations[0].description == "cold"
    assert blueprint.locations[0].location_type == "hall"
    assert blueprint.clues[0].name == "Letter"
    assert blueprint.clues[0].initial_holder_character_key == "butler"
    assert blueprint.events[0].name == "Alarm"
    assert blueprint.events[0].participants[0].character_key == "butler"
