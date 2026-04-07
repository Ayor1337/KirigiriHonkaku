import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ai.game_generation import GameGenerationBlueprintValidationError, GameGenerationRuntime
from app.schemas.world_generation import WorldBlueprint
from app.seeds.world import DefaultWorldSeedProvider


def _parse_sse_events(response) -> list[tuple[str, dict]]:
    raw_text = ""
    for chunk in response.iter_text():
        raw_text += chunk

    events: list[tuple[str, dict]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            if line.startswith("data: "):
                data_lines.append(line.removeprefix("data: ").strip())
        if event_name:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


class ProgressRuntime(GameGenerationRuntime):
    def generate(self, *, session_uuid: str, progress_callback=None) -> WorldBlueprint:
        if progress_callback:
            progress_callback("world_planning", {})
            progress_callback("world_generating", {})
            progress_callback("world_validating", {"attempt": 1, "max_attempts": 3})
            progress_callback("world_fixing", {"attempt": 1, "max_attempts": 3})
            progress_callback("world_validating", {"attempt": 2, "max_attempts": 3})

        seed = DefaultWorldSeedProvider().resolve(
            SimpleNamespace(
                case_template_key="case-manor",
                map_template_key="map-manor",
                truth_template_key="truth-manor",
            )
        )
        return WorldBlueprint.model_validate(
            {
                "title": f"Generated Case {session_uuid[:8]}",
                **seed,
            }
        )


class FailingRuntime(GameGenerationRuntime):
    def generate(self, *, session_uuid: str, progress_callback=None) -> WorldBlueprint:
        if progress_callback:
            progress_callback("world_planning", {})
            progress_callback("world_generating", {})
            progress_callback("world_validating", {"attempt": 1, "max_attempts": 3})
        raise GameGenerationBlueprintValidationError(["broken blueprint"])


def test_bootstrap_stream_emits_stage_events_in_order_and_completes(app):
    runtime = ProgressRuntime()
    app.state.container.game_generation_runtime = runtime
    app.state.container.world_bootstrap_service._generation_runtime = runtime

    with TestClient(app) as client:
        with client.stream("POST", "/api/v1/sessions/bootstrap-stream") as response:
            events = _parse_sse_events(response)

    assert response.status_code == 200
    assert [event_name for event_name, _ in events] == [
        "stage",
        "stage",
        "stage",
        "stage",
        "stage",
        "stage",
        "stage",
        "stage",
        "stage",
        "complete",
    ]

    placeholders = [payload["placeholder"] for _, payload in events[:-1]]
    assert placeholders == [
        "session_creating",
        "session_created",
        "world_planning",
        "world_generating",
        "world_validating",
        "world_fixing",
        "world_validating",
        "world_persisting",
        "world_ready",
    ]
    assert events[-1][1]["status"] == "ready"
    assert "player_id" in events[-1][1]["root_ids"]
    assert "map_id" in events[-1][1]["root_ids"]


def test_bootstrap_stream_emits_error_and_rolls_back_to_draft(app):
    runtime = FailingRuntime()
    app.state.container.game_generation_runtime = runtime
    app.state.container.world_bootstrap_service._generation_runtime = runtime

    with TestClient(app) as client:
        with client.stream("POST", "/api/v1/sessions/bootstrap-stream") as response:
            events = _parse_sse_events(response)

    assert response.status_code == 200
    assert [event_name for event_name, _ in events] == ["stage", "stage", "stage", "stage", "stage", "error"]
    error_payload = events[-1][1]
    session_id = error_payload["session_id"]
    assert error_payload["code"] == "generation_failed"
    assert error_payload["failed_placeholder"] == "world_validating"

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(session_id)

    assert session is not None
    assert session.status == "draft"
    assert session.title is None
    assert session.truth_payload == {}
