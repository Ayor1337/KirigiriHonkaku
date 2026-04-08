from fastapi.testclient import TestClient

from app.ai.game_generation import (
    GameGenerationBlueprintValidationError,
    GameGenerationRuntime,
    ProgressCallback,
    UnavailableGameGenerationRuntime,
)
from tests.game_generation_fakes import StaticGameGenerationRuntime


class ValidationFailingGameGenerationRuntime(GameGenerationRuntime):
    def generate(self, *, session_uuid: str, progress_callback: ProgressCallback = None):
        raise GameGenerationBlueprintValidationError(["truth.required_clue_keys must contain at least one clue key."])


def _set_runtime(app, runtime: GameGenerationRuntime) -> None:
    app.state.container.game_generation_runtime = runtime
    app.state.container.world_bootstrap_service._generation_runtime = runtime


def test_bootstrap_reports_provider_unavailable_and_keeps_draft(app):
    _set_runtime(app, UnavailableGameGenerationRuntime())

    with TestClient(app) as client:
        created = client.post("/api/v1/sessions").json()
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        fetched = client.get(f"/api/v1/sessions/{created['id']}")

    assert response.status_code == 503
    assert response.json()["detail"] == "Game generation runtime is not configured."
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "draft"
    assert fetched.json()["title"] is None


def test_bootstrap_reports_validation_error_and_keeps_draft(app):
    _set_runtime(app, ValidationFailingGameGenerationRuntime())

    with TestClient(app) as client:
        created = client.post("/api/v1/sessions").json()
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        fetched = client.get(f"/api/v1/sessions/{created['id']}")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Generated world blueprint failed validation."
    assert response.json()["detail"]["errors"] == ["truth.required_clue_keys must contain at least one clue key."]
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "draft"
    assert fetched.json()["title"] is None

    _set_runtime(app, StaticGameGenerationRuntime())
