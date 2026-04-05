from pathlib import Path

from fastapi.testclient import TestClient


def _create_session(client: TestClient, title: str = "Bootstrap Case") -> dict:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": title,
            "case_template_key": "case-zero",
            "map_template_key": "map-zero",
            "truth_template_key": "truth-zero",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_bootstrap_world_builds_minimal_world_state_and_marks_session_ready(app):
    with TestClient(app) as client:
        created = _create_session(client)
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        fetched = client.get(f"/api/v1/sessions/{created['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == created["id"]
    assert payload["status"] == "ready"
    assert payload["created_counts"] == {
        "characters": 3,
        "players": 1,
        "npcs": 2,
        "locations": 3,
        "connections": 2,
        "clues": 2,
        "events": 1,
        "dialogues": 0,
    }
    assert "player_id" in payload["root_ids"]
    assert "map_id" in payload["root_ids"]
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "ready"


def test_bootstrap_world_rejects_duplicate_initialization(app):
    with TestClient(app) as client:
        created = _create_session(client, title="Bootstrap Once")
        first_response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        second_response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Session world state has already been bootstrapped."


def test_bootstrap_world_writes_truth_file_and_payload(app):
    with TestClient(app) as client:
        created = _create_session(client, title="Truth Bootstrap Case")
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")

    assert response.status_code == 200

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(created["id"])

    assert session is not None
    assert session.truth_file_path
    assert session.truth_payload is not None
    assert session.truth_payload["culprit_npc_key"] == "journalist"
    assert session.truth_payload["required_clue_keys"] == ["torn-note"]

    truth_path = Path(session.truth_file_path)
    assert truth_path.exists()
    truth_text = truth_path.read_text(encoding="utf-8")
    assert "journalist" in truth_text
    assert "torn-note" in truth_text
