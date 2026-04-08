from fastapi.testclient import TestClient

from tests.api.test_actions import _bootstrap_session


def test_get_board_returns_not_found_before_bootstrap(app):
    with TestClient(app) as client:
        created = client.post("/api/v1/sessions").json()
        response = client.get(f"/api/v1/sessions/{created['id']}/board")

    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found for session."


def test_put_board_replaces_board_content_and_can_be_read_back(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)

        with app.state.container.uow_factory() as uow:
            player = uow.players.get_by_session(session_id)
            assert player is not None
            assert player.detective_board is not None
            clue = next(item for item in uow.clues.list_by_session(session_id) if item.key == "torn-note")
            npc = next(item for item in uow.npcs.list_by_session(session_id) if item.template_key == "journalist")

        save_response = client.put(
            f"/api/v1/sessions/{session_id}/board",
            json={
                "board_layout_version": 1,
                "items": [
                    {
                        "client_key": "item-clue",
                        "target_type": "clue",
                        "target_ref_id": str(clue.id),
                        "position_x": 120.5,
                        "position_y": 80.0,
                        "group_key": "evidence",
                    },
                    {
                        "client_key": "item-npc",
                        "target_type": "npc",
                        "target_ref_id": str(npc.id),
                        "position_x": 260.0,
                        "position_y": 80.0,
                        "group_key": "suspects",
                    },
                ],
                "links": [
                    {
                        "from_client_key": "item-clue",
                        "to_client_key": "item-npc",
                        "label": "points-to",
                        "style_key": "solid",
                    }
                ],
                "notes": [
                    {
                        "content": "需要核对记者的不在场证明",
                        "position_x": 320.0,
                        "position_y": 180.0,
                    }
                ],
            },
        )
        fetch_response = client.get(f"/api/v1/sessions/{session_id}/board")

    assert save_response.status_code == 200
    saved_payload = save_response.json()
    assert saved_payload["board_layout_version"] == 1
    assert len(saved_payload["items"]) == 2
    assert {item["target_type"] for item in saved_payload["items"]} == {"clue", "npc"}
    assert len(saved_payload["links"]) == 1
    assert saved_payload["links"][0]["label"] == "points-to"
    assert len(saved_payload["notes"]) == 1
    assert saved_payload["notes"][0]["content"] == "需要核对记者的不在场证明"

    assert fetch_response.status_code == 200
    fetched_payload = fetch_response.json()
    assert fetched_payload == saved_payload


def test_put_board_rejects_item_target_outside_session(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        response = client.put(
            f"/api/v1/sessions/{session_id}/board",
            json={
                "board_layout_version": 1,
                "items": [
                    {
                        "client_key": "item-invalid",
                        "target_type": "clue",
                        "target_ref_id": "00000000-0000-0000-0000-000000000000",
                        "position_x": 0,
                        "position_y": 0,
                        "group_key": None,
                    }
                ],
                "links": [],
                "notes": [],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Board item target does not exist in current session."


def test_get_board_returns_bootstrap_reachable_locations_with_generated_text(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        response = client.get(f"/api/v1/sessions/{session_id}/board")

    assert response.status_code == 200
    payload = response.json()
    assert {item["target_type"] for item in payload["items"]} == {"location"}
    assert {item["title"] for item in payload["items"]} == {"Archive Room", "Garden Gate"}
    content_by_title = {item["title"]: item["content"] for item in payload["items"]}
    assert content_by_title["Archive Room"] == "存放旧档案和纸质材料的房间。"
    assert content_by_title["Garden Gate"] == "通往庭院外侧的小门。"


def test_investigate_auto_adds_new_clue_board_item_with_generated_text(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        move_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": session_id,
                "action_type": "move",
                "actor_id": "player",
                "payload": {"target_location_key": "archive-room"},
            },
        )
        assert move_response.status_code == 200

        investigate_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": session_id,
                "action_type": "investigate",
                "actor_id": "player",
                "payload": {},
            },
        )
        assert investigate_response.status_code == 200

        board_response = client.get(f"/api/v1/sessions/{session_id}/board")

    assert board_response.status_code == 200
    payload = board_response.json()
    clue_items = [item for item in payload["items"] if item["target_type"] == "clue"]
    assert len(clue_items) == 1
    assert clue_items[0]["title"] == "Torn Note"
    assert clue_items[0]["content"] == "在档案室文件夹里发现的一页残缺便条。"



def test_get_board_returns_bootstrap_visible_npcs_with_generated_text(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        response = client.get(f"/api/v1/sessions/{session_id}/board")

    assert response.status_code == 200
    payload = response.json()
    npc_items = [item for item in payload["items"] if item["target_type"] == "npc"]
    assert len(npc_items) == 2
    assert {item["title"] for item in npc_items} == {"Journalist Ren", "Caretaker Mo"}
    content_by_title = {item["title"]: item["content"] for item in npc_items}
    assert content_by_title["Journalist Ren"] == "Freelance Reporter"
    assert content_by_title["Caretaker Mo"] == "Estate Caretaker"
