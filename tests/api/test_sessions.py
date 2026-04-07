from fastapi.testclient import TestClient


def test_create_session_initializes_db_record_and_data_tree(app):
    with TestClient(app) as client:
        response = client.post("/api/v1/sessions")

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] is None
    assert payload["status"] == "draft"
    assert payload["data_directories"]["session_root"].endswith(payload["uuid"])


def test_get_session_returns_existing_session(app):
    with TestClient(app) as client:
        created = client.post("/api/v1/sessions").json()
        fetched = client.get(f"/api/v1/sessions/{created['id']}")
        fetched_state = client.get(f"/api/v1/sessions/{created['id']}/state")
        fetched_player = client.get(f"/api/v1/sessions/{created['id']}/player")
        fetched_map = client.get(f"/api/v1/sessions/{created['id']}/map")

    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["id"] == created["id"]
    assert payload["title"] is None
    assert payload["root_ids"] == {}
    assert "player" not in payload
    assert "map" not in payload
    assert "exposure_value" not in payload
    assert "exposure_level" not in payload

    assert fetched_state.status_code == 200
    assert fetched_state.json() == {
        "exposure_value": 0,
        "exposure_level": "low",
    }

    assert fetched_player.status_code == 404
    assert fetched_player.json()["detail"] == "Player not found for session."

    assert fetched_map.status_code == 404
    assert fetched_map.json()["detail"] == "Map not found for session."




def test_get_session_npcs_returns_empty_list_before_bootstrap(app):
    with TestClient(app) as client:
        created = client.post("/api/v1/sessions").json()
        fetched_npcs = client.get(f"/api/v1/sessions/{created['id']}/npcs")

    assert fetched_npcs.status_code == 200
    assert fetched_npcs.json() == []
def test_list_sessions_returns_all_sessions_in_created_desc_order(app):
    with TestClient(app) as client:
        first = client.post("/api/v1/sessions").json()
        second = client.post("/api/v1/sessions").json()
        listed = client.get("/api/v1/sessions")

    assert listed.status_code == 200
    payload = listed.json()
    assert isinstance(payload, list)
    assert [item["id"] for item in payload] == [second["id"], first["id"]]
    assert payload[0]["title"] is None
    assert "data_directories" not in payload[0]
    assert "root_ids" not in payload[0]
