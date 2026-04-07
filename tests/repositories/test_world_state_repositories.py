from fastapi.testclient import TestClient


def _bootstrap_session(app) -> str:
    with TestClient(app) as client:
        created = client.post("/api/v1/sessions")
        assert created.status_code == 201
        session_id = created.json()["id"]
        bootstrapped = client.post(f"/api/v1/sessions/{session_id}/bootstrap")
        assert bootstrapped.status_code == 200
    return session_id


def test_uow_exposes_bootstrapped_world_state_aggregates(app):
    session_id = _bootstrap_session(app)

    with app.state.container.uow_factory() as uow:
        player = uow.players.get_by_session(session_id)
        npc_list = uow.npcs.list_by_session(session_id)
        game_map = uow.maps.get_by_session(session_id)
        clue_list = uow.clues.list_by_session(session_id)
        event_list = uow.events.list_by_session(session_id)
        dialogue_list = uow.dialogues.list_by_session(session_id)

    assert player is not None
    assert player.character.kind == "player"
    assert player.state is not None
    assert player.inventory is not None
    assert player.knowledge is not None
    assert player.detective_board is not None

    assert len(npc_list) == 2
    assert all(npc.character.kind == "npc" for npc in npc_list)
    assert all(npc.state is not None for npc in npc_list)
    assert all(npc.schedule is not None for npc in npc_list)
    assert all(len(npc.schedule.entries) == 1 for npc in npc_list)

    assert game_map is not None
    assert len(game_map.locations) == 3
    assert len(game_map.connections) == 2

    assert len(clue_list) == 2
    assert any(clue.current_holder_character is not None for clue in clue_list)
    assert any(clue.current_location is not None for clue in clue_list)

    assert len(event_list) == 1
    assert len(event_list[0].participants) == 2
    assert dialogue_list == []
