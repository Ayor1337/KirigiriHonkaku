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
