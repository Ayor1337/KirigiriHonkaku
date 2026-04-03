from fastapi.testclient import TestClient


def test_create_session_initializes_db_record_and_data_tree(app):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "Case Zero",
                "case_template_key": "case-zero",
                "map_template_key": "map-zero",
                "truth_template_key": "truth-zero",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Case Zero"
    assert payload["status"] == "draft"
    assert payload["data_directories"]["session_root"].endswith(payload["uuid"])


def test_get_session_returns_existing_session(app):
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/sessions",
            json={
                "title": "Case Fetch",
                "case_template_key": "case-fetch",
                "map_template_key": "map-fetch",
                "truth_template_key": "truth-fetch",
            },
        ).json()
        fetched = client.get(f"/api/v1/sessions/{created['id']}")

    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["id"] == created["id"]
    assert payload["title"] == "Case Fetch"
