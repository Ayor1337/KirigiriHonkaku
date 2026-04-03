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


def _bootstrap_session(client: TestClient, title: str = "Action Case") -> str:
    session_id = _create_session(client, title=title)["id"]
    bootstrap_response = client.post(f"/api/v1/sessions/{session_id}/bootstrap")
    assert bootstrap_response.status_code == 200
    return session_id


def _submit_action(
    client: TestClient,
    session_id: str,
    action_type: str,
    payload: dict,
    actor_id: str = "player",
) -> dict:
    action_response = client.post(
        "/api/v1/actions",
        json={
            "session_id": session_id,
            "action_type": action_type,
            "actor_id": actor_id,
            "payload": payload,
        },
    )
    assert action_response.status_code == 200
    return action_response.json()


def test_submit_action_rejects_draft_session_before_world_bootstrap(app):
    with TestClient(app) as client:
        created = _create_session(client, title="Draft Action Case")
        action_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": created["id"],
                "action_type": "move",
                "actor_id": "player",
                "payload": {"target_location_key": "archive-room"},
            },
        )

    assert action_response.status_code == 409
    assert action_response.json()["detail"] == "Session world state has not been bootstrapped."


def test_move_action_updates_world_state_and_scene_snapshot(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        payload = _submit_action(
            client,
            session_id,
            "move",
            {"target_location_key": "archive-room"},
        )

    assert payload["status"] == "accepted"
    assert payload["action_type"] == "move"
    assert payload["state_delta_summary"]["current_time_minute"] == 5
    assert payload["state_delta_summary"]["movement"]["from_location_key"] == "entrance-hall"
    assert payload["state_delta_summary"]["movement"]["to_location_key"] == "archive-room"
    assert payload["scene_snapshot"]["session_id"] == session_id
    assert payload["scene_snapshot"]["details"]["current_location"]["key"] == "archive-room"
    assert {item["key"] for item in payload["scene_snapshot"]["details"]["reachable_locations"]} == {
        "entrance-hall"
    }
    assert [item["key"] for item in payload["scene_snapshot"]["details"]["visible_npcs"]] == ["journalist"]
    assert payload["soft_state_patch"]["allowed"] is True

    with app.state.container.uow_factory() as uow:
        player = uow.players.get_by_session(session_id)
        session = uow.sessions.get(session_id)
        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(session_id)}

    assert player is not None
    assert player.character.current_location is not None
    assert player.character.current_location.name == "Archive Room"
    assert session is not None
    assert session.current_time_minute == 5
    assert npcs["caretaker"].state.current_location is not None
    assert npcs["caretaker"].state.current_location.name == "Garden Gate"


def test_move_action_rejects_unreachable_target_without_advancing_time(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        payload = _submit_action(
            client,
            session_id,
            "move",
            {"target_location_key": "does-not-exist"},
        )

    assert payload["status"] == "rejected"
    assert payload["errors"] == ["Target location does not exist."]
    assert payload["state_delta_summary"]["hard_state_updated"] is False

    with app.state.container.uow_factory() as uow:
        player = uow.players.get_by_session(session_id)
        session = uow.sessions.get(session_id)

    assert player is not None
    assert player.character.current_location is not None
    assert player.character.current_location.name == "Entrance Hall"
    assert session is not None
    assert session.current_time_minute == 0


def test_investigate_action_collects_local_clues_and_updates_knowledge(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        payload = _submit_action(client, session_id, "investigate", {})

    assert payload["status"] == "accepted"
    assert payload["action_type"] == "investigate"
    assert payload["state_delta_summary"]["current_time_minute"] == 10
    assert [item["key"] for item in payload["state_delta_summary"]["investigation"]["discovered_clues"]] == [
        "torn-note"
    ]
    assert payload["scene_snapshot"]["details"]["investigable_clues"] == []

    with app.state.container.uow_factory() as uow:
        player = uow.players.get_by_session(session_id)
        clues = uow.clues.list_by_session(session_id)

    assert player is not None
    assert player.knowledge is not None
    assert any(entry.title == "Torn Note" for entry in player.knowledge.entries)
    torn_note = next(clue for clue in clues if clue.name == "Torn Note")
    assert torn_note.current_holder_character is not None
    assert torn_note.current_holder_character.kind == "player"
    assert torn_note.current_location is None


def test_talk_action_creates_dialogue_when_npc_is_in_same_location(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        payload = _submit_action(client, session_id, "talk", {"target_npc_key": "journalist"})

    assert payload["status"] == "accepted"
    assert payload["action_type"] == "talk"
    assert payload["state_delta_summary"]["current_time_minute"] == 10
    assert payload["state_delta_summary"]["dialogue"]["target_npc_key"] == "journalist"
    assert payload["scene_snapshot"]["details"]["latest_dialogue"]["target_npc_key"] == "journalist"
    assert payload["scene_snapshot"]["details"]["latest_dialogue"]["location_key"] == "archive-room"

    with app.state.container.uow_factory() as uow:
        dialogues = uow.dialogues.list_by_session(session_id)
        session = uow.sessions.get(session_id)

    assert session is not None
    assert session.current_time_minute == 10
    assert len(dialogues) == 1
    assert len(dialogues[0].participants) == 2


def test_talk_action_rejects_npc_outside_current_location(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        payload = _submit_action(client, session_id, "talk", {"target_npc_key": "journalist"})

    assert payload["status"] == "rejected"
    assert payload["errors"] == ["Target NPC is not available in the current location."]

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        dialogues = uow.dialogues.list_by_session(session_id)

    assert session is not None
    assert session.current_time_minute == 0
    assert dialogues == []
