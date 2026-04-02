from fastapi.testclient import TestClient


def test_submit_action_returns_structured_action_result(app):
    with TestClient(app) as client:
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "Action Case",
                "case_template_key": "case-action",
                "map_template_key": "map-action",
                "truth_template_key": "truth-action",
            },
        )
        session_id = session_response.json()["id"]

        action_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": session_id,
                "action_type": "move",
                "actor_id": "player",
                "payload": {"target_location_id": "lobby"},
            },
        )

    assert action_response.status_code == 200
    payload = action_response.json()
    assert payload["status"] == "accepted"
    assert payload["action_type"] == "move"
    assert payload["state_delta_summary"]["hard_state_updated"] is True
    assert payload["scene_snapshot"]["session_id"] == session_id
    assert payload["soft_state_patch"]["allowed"] is True
