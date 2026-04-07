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

    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["id"] == created["id"]
    assert payload["title"] is None
    assert payload["root_ids"] == {}
    assert payload["player"] is None
    assert payload["map"] is None
    assert payload["exposure_value"] == 0
    assert payload["exposure_level"] == "low"


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
