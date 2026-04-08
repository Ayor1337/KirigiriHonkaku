import shutil
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


EXPECTED_TABLES = {
    "session",
    "character",
    "player",
    "player_state",
    "player_inventory",
    "player_knowledge",
    "knowledge_entry",
    "knowledge_topic",
    "detective_board",
    "board_item",
    "board_link",
    "board_note",
    "npc",
    "npc_state",
    "npc_schedule",
    "schedule_entry",
    "map",
    "location",
    "connection",
    "clue",
    "event",
    "event_participant",
    "dialogue",
    "dialogue_participant",
    "utterance",
}

EXPECTED_COLUMNS = {
    "location": {"key"},
    "clue": {"key", "discovery_rule"},
    "session": {"truth_payload"},
    "board_item": {"title", "content"},
}


def test_alembic_upgrade_applies_fixed_schema_snapshot():
    runtime_root = Path("tests_runtime") / f"alembic-{uuid4().hex}"
    runtime_root.mkdir(parents=True, exist_ok=True)
    database_path = runtime_root / "alembic_step2.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path}")

    try:
        command.upgrade(config, "head")

        engine = create_engine(f"sqlite+pysqlite:///{database_path}")
        try:
            inspector = inspect(engine)
            assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))

            session_columns = {column["name"] for column in inspector.get_columns("session")}
            assert {"truth_payload", "story_markdown", "history_markdown", "truth_markdown", "latest_action_payload", "ai_generation_log_entries"}.issubset(session_columns)
            assert {"story_file_path", "history_file_path", "truth_file_path"}.isdisjoint(session_columns)

            npc_columns = {column["name"] for column in inspector.get_columns("npc")}
            assert {"profile_markdown", "memory_markdown"}.issubset(npc_columns)
            assert {"profile_file_path", "memory_file_path"}.isdisjoint(npc_columns)

            clue_columns = {column["name"] for column in inspector.get_columns("clue")}
            assert {"key", "discovery_rule", "document_markdown"}.issubset(clue_columns)
            assert "document_file_path" not in clue_columns

            dialogue_columns = {column["name"] for column in inspector.get_columns("dialogue")}
            assert {"summary_markdown", "transcript_markdown"}.issubset(dialogue_columns)
            assert {"summary_file_path", "transcript_file_path"}.isdisjoint(dialogue_columns)

            location_columns = {column["name"] for column in inspector.get_columns("location")}
            assert "key" in location_columns

            board_item_columns = {column["name"] for column in inspector.get_columns("board_item")}
            assert {"title", "content"}.issubset(board_item_columns)
        finally:
            engine.dispose()
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)

