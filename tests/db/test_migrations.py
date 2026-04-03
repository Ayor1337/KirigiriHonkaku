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
        finally:
            engine.dispose()
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)
