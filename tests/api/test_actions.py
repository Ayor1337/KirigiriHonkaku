from fastapi.testclient import TestClient


def _create_session(client: TestClient, title: str = "Action Case") -> dict:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": title,
            "case_template_key": "case-action",
            "map_template_key": "map-action",
            "truth_template_key": "truth-action",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_submit_action_rejects_draft_session_before_world_bootstrap(app):
    with TestClient(app) as client:
        created = _create_session(client, title="Draft Action Case")
        action_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": created["id"],
                "action_type": "move",
                "actor_id": "player",
                "payload": {"target_location_id": "archive-room"},
            },
        )

    assert action_response.status_code == 409
    assert action_response.json()["detail"] == "Session world state has not been bootstrapped."


def test_submit_action_returns_structured_action_result(app):
    with TestClient(app) as client:
        session_id = _create_session(client)["id"]
        bootstrap_response = client.post(f"/api/v1/sessions/{session_id}/bootstrap")
        assert bootstrap_response.status_code == 200

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
