from pathlib import Path

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
    assert payload["narrative_text"]
    assert payload["storage_refs"]["dialogue_summary"]
    assert payload["storage_refs"]["dialogue_transcript"]
    assert payload["storage_refs"]["history_markdown"]
    assert payload["storage_refs"]["npc_memory:journalist"]

    with app.state.container.uow_factory() as uow:
        dialogues = uow.dialogues.list_by_session(session_id)
        session = uow.sessions.get(session_id)
        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(session_id)}

    assert session is not None
    assert session.current_time_minute == 10
    assert len(dialogues) == 1
    assert len(dialogues[0].participants) == 2
    assert dialogues[0].summary_file_path
    assert dialogues[0].transcript_file_path
    assert len(dialogues[0].utterances) >= 1
    assert npcs["journalist"].memory_file_path
    assert npcs["journalist"].state.attitude_to_player == "guarded"
    assert npcs["journalist"].state.emotion_tag == "wary"

    transcript_path = Path(dialogues[0].transcript_file_path)
    summary_path = Path(dialogues[0].summary_file_path)
    memory_path = Path(npcs["journalist"].memory_file_path)
    history_path = Path(payload["storage_refs"]["history_markdown"])

    assert transcript_path.exists()
    assert summary_path.exists()
    assert memory_path.exists()
    assert history_path.exists()
    assert "Journalist" in transcript_path.read_text(encoding="utf-8")
    assert "archive-room" in summary_path.read_text(encoding="utf-8")
    assert "本次对话更新" in memory_path.read_text(encoding="utf-8")
    assert payload["narrative_text"] in history_path.read_text(encoding="utf-8")


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


def test_gather_action_creates_public_context_and_raises_exposure(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        _submit_action(client, session_id, "investigate", {})
        payload = _submit_action(
            client,
            session_id,
            "gather",
            {"location_key": "archive-room", "reason": "public accusation"},
        )

    assert payload["status"] == "accepted"
    assert payload["action_type"] == "gather"
    assert payload["state_delta_summary"]["public_context"]["is_public"] is True
    assert payload["state_delta_summary"]["public_context"]["source"] == "gather"
    assert payload["state_delta_summary"]["exposure"]["level"] == "medium"
    assert payload["state_delta_summary"]["risk"]["countermeasure_triggered"] is True

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        events = uow.events.list_by_session(session_id)
        npcs = {npc.template_key: npc for npc in uow.npcs.list_by_session(session_id)}

    assert session is not None
    assert session.current_time_minute == 15
    assert session.exposure_level == "medium"
    assert any(event.event_type == "player_gathering" and event.is_public_event for event in events)
    assert npcs["journalist"].state is not None
    assert npcs["journalist"].state.is_under_pressure is True


def test_public_accuse_succeeds_with_required_evidence(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        _submit_action(client, session_id, "investigate", {})
        _submit_action(client, session_id, "gather", {"location_key": "archive-room", "reason": "public accusation"})
        payload = _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "journalist",
                "context_mode": "public",
                "evidence_clue_keys": ["torn-note"],
                "force_strategy": "standard",
            },
        )

    assert payload["status"] == "accepted"
    assert payload["state_delta_summary"]["ending"]["ending_type"] == "success"
    assert payload["state_delta_summary"]["accusation"]["resolution"] == "success"
    assert payload["state_delta_summary"]["public_context"]["is_public"] is True

    with app.state.container.uow_factory() as uow:
        session = uow.sessions.get(session_id)

    assert session is not None
    assert session.status == "ended"
    assert session.ending_type == "success"
    assert session.accusation_state == "resolved"


def test_public_accuse_without_required_evidence_fails_to_convict(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        _submit_action(client, session_id, "gather", {"location_key": "archive-room", "reason": "public accusation"})
        payload = _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "journalist",
                "context_mode": "public",
                "evidence_clue_keys": [],
                "force_strategy": "standard",
            },
        )

    assert payload["status"] == "accepted"
    assert payload["state_delta_summary"]["ending"]["ending_type"] == "failure_insufficient_evidence"
    assert payload["state_delta_summary"]["accusation"]["resolution"] == "insufficient_evidence"


def test_private_accuse_true_culprit_without_countermeasure_support_causes_player_death(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        payload = _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "journalist",
                "context_mode": "private",
                "evidence_clue_keys": ["torn-note"],
                "force_strategy": "standard",
            },
        )

    assert payload["status"] == "accepted"
    assert payload["state_delta_summary"]["ending"]["ending_type"] == "failure_killed_by_culprit"
    assert payload["state_delta_summary"]["accusation"]["resolution"] == "culprit_counterattack"


def test_private_accuse_true_culprit_with_violent_option_can_become_pseudo_victory(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        with app.state.container.uow_factory() as uow:
            player = uow.players.get_by_session(session_id)
            assert player is not None
            assert player.state is not None
            player.state.status_flags = {
                **player.state.status_flags,
                "can_counterattack_culprit": True,
            }
            uow.commit()

        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        payload = _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "journalist",
                "context_mode": "private",
                "evidence_clue_keys": ["torn-note"],
                "force_strategy": "violent",
            },
        )

    assert payload["status"] == "accepted"
    assert payload["state_delta_summary"]["ending"]["ending_type"] == "pseudo_victory_kill_culprit"
    assert payload["state_delta_summary"]["accusation"]["resolution"] == "violent_resolution"


def test_public_fabricated_accusation_can_reach_false_verdict_pseudo_victory(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        with app.state.container.uow_factory() as uow:
            player = uow.players.get_by_session(session_id)
            assert player is not None
            assert player.state is not None
            player.state.status_flags = {
                **player.state.status_flags,
                "can_fabricate_evidence": True,
            }
            uow.commit()

        payload = _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "caretaker",
                "context_mode": "public",
                "evidence_clue_keys": [],
                "force_strategy": "fabricate",
            },
        )

    assert payload["status"] == "accepted"
    assert payload["state_delta_summary"]["ending"]["ending_type"] == "pseudo_victory_false_verdict"
    assert payload["state_delta_summary"]["accusation"]["resolution"] == "fabricated_verdict"

def test_submit_action_rejects_ended_session(app):
    with TestClient(app) as client:
        session_id = _bootstrap_session(client)
        _submit_action(client, session_id, "move", {"target_location_key": "archive-room"})
        _submit_action(client, session_id, "investigate", {})
        _submit_action(client, session_id, "gather", {"location_key": "archive-room", "reason": "public accusation"})
        _submit_action(
            client,
            session_id,
            "accuse",
            {
                "target_npc_key": "journalist",
                "context_mode": "public",
                "evidence_clue_keys": ["torn-note"],
                "force_strategy": "standard",
            },
        )
        action_response = client.post(
            "/api/v1/actions",
            json={
                "session_id": session_id,
                "action_type": "move",
                "actor_id": "player",
                "payload": {"target_location_key": "entrance-hall"},
            },
        )

    assert action_response.status_code == 409
    assert action_response.json()["detail"] == "Session has already ended."
