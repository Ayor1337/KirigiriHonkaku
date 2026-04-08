from pathlib import Path

from fastapi.testclient import TestClient


def _create_session(client: TestClient) -> dict:
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    return response.json()


def test_bootstrap_world_builds_minimal_world_state_and_marks_session_ready(app):
    with TestClient(app) as client:
        created = _create_session(client)
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        fetched = client.get(f"/api/v1/sessions/{created['id']}")
        fetched_state = client.get(f"/api/v1/sessions/{created['id']}/state")
        fetched_player = client.get(f"/api/v1/sessions/{created['id']}/player")
        fetched_map = client.get(f"/api/v1/sessions/{created['id']}/map")
        fetched_board = client.get(f"/api/v1/sessions/{created['id']}/board")

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
    fetched_payload = fetched.json()
    assert fetched_payload["status"] == "ready"
    assert fetched_payload["title"].startswith("Generated Case ")
    assert fetched_payload["story_markdown"]
    assert fetched_payload["root_ids"] == payload["root_ids"]
    assert "player" not in fetched_payload
    assert "map" not in fetched_payload
    assert "exposure_value" not in fetched_payload
    assert "exposure_level" not in fetched_payload

    assert fetched_state.status_code == 200
    assert fetched_state.json() == {
        "exposure_value": 0,
        "exposure_level": "low",
    }

    assert fetched_player.status_code == 200
    fetched_player_payload = fetched_player.json()
    with app.state.container.uow_factory() as uow:
        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(created["id"])}

    assert npcs["journalist"].state is not None
    assert npcs["journalist"].state.has_met_player is False

    assert fetched_player_payload == {
        "id": payload["root_ids"]["player_id"],
        "character_id": fetched_player_payload["character_id"],
        "display_name": "Detective Kirigiri",
        "public_identity": "Independent Detective",
        "template_key": "case-manor",
        "template_name": "Detective",
        "trait_text": "冷静、谨慎、擅长交叉验证证词。",
        "background_text": "受邀前来调查庄园中的异常事件。",
        "current_location_id": fetched_player_payload["current_location_id"],
        "current_location_name": "Entrance Hall",
        "exposure_value": 0,
        "exposure_level": "low",
    }

    assert fetched_map.status_code == 200
    assert fetched_board.status_code == 200
    fetched_board_payload = fetched_board.json()
    assert len(fetched_board_payload["items"]) == 4
    assert {item["title"] for item in fetched_board_payload["items"]} == {"Archive Room", "Garden Gate", "Journalist Ren", "Caretaker Mo"}
    fetched_map_payload = fetched_map.json()
    locations_by_key = {item["key"]: item for item in fetched_map_payload["locations"]}
    connections = fetched_map_payload["connections"]

    assert fetched_map_payload == {
        "id": payload["root_ids"]["map_id"],
        "template_key": "map-manor",
        "display_name": "Moonview Manor",
        "locations": [
            {
                "id": locations_by_key["archive-room"]["id"],
                "key": "archive-room",
                "parent_location_id": locations_by_key["entrance-hall"]["id"],
                "name": "Archive Room",
                "description": "存放旧档案和纸质材料的房间。",
                "location_type": "interior",
                "visibility_level": "restricted",
                "is_hidden": False,
                "status_flags": {},
            },
            {
                "id": locations_by_key["entrance-hall"]["id"],
                "key": "entrance-hall",
                "parent_location_id": None,
                "name": "Entrance Hall",
                "description": "庄园的主入口与交通枢纽。",
                "location_type": "hub",
                "visibility_level": "public",
                "is_hidden": False,
                "status_flags": {},
            },
            {
                "id": locations_by_key["garden-gate"]["id"],
                "key": "garden-gate",
                "parent_location_id": locations_by_key["entrance-hall"]["id"],
                "name": "Garden Gate",
                "description": "通往庭院外侧的小门。",
                "location_type": "exterior",
                "visibility_level": "public",
                "is_hidden": False,
                "status_flags": {},
            },
        ],
        "connections": [
            {
                "id": connections[0]["id"],
                "from_location_id": locations_by_key["entrance-hall"]["id"],
                "to_location_id": locations_by_key["archive-room"]["id"],
                "connection_type": "door",
                "access_rule": {},
                "is_hidden": False,
                "is_locked": False,
                "is_one_way": False,
                "is_dangerous": False,
                "time_window_rule": {},
            },
            {
                "id": connections[1]["id"],
                "from_location_id": locations_by_key["entrance-hall"]["id"],
                "to_location_id": locations_by_key["garden-gate"]["id"],
                "connection_type": "gate",
                "access_rule": {},
                "is_hidden": False,
                "is_locked": False,
                "is_one_way": False,
                "is_dangerous": False,
                "time_window_rule": {},
            },
        ],
    }


def test_bootstrap_world_rejects_duplicate_initialization(app):
    with TestClient(app) as client:
        created = _create_session(client)
        first_response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")
        second_response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Session world state has already been bootstrapped."


def test_bootstrap_world_writes_truth_file_and_payload(app):
    with TestClient(app) as client:
        created = _create_session(client)
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")

    assert response.status_code == 200

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(created["id"])

    assert session is not None
    assert session.title and session.title.startswith("Generated Case ")
    assert session.truth_markdown
    assert session.truth_payload is not None
    assert session.truth_payload["culprit_npc_key"] == "journalist"
    assert session.truth_payload["required_clue_keys"] == ["torn-note"]
    assert "journalist" in session.truth_markdown
    assert "torn-note" in session.truth_markdown


def test_bootstrap_world_writes_story_opening_for_player(app):
    with TestClient(app) as client:
        created = _create_session(client)
        response = client.post(f"/api/v1/sessions/{created['id']}/bootstrap")

    assert response.status_code == 200

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(created["id"])

    assert session is not None
    assert session.story_markdown
    assert session.story_markdown.strip()
    assert session.title in session.story_markdown
    assert "你" in session.story_markdown
    assert "Entrance Hall" in session.story_markdown
    assert "entrance-hall" not in session.story_markdown
    assert "journalist" not in session.story_markdown
