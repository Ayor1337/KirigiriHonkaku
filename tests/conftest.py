import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.main import create_app
from tests.game_generation_fakes import StaticGameGenerationRuntime


@pytest.fixture
def app():
    runtime_root = Path("tests_runtime") / uuid4().hex
    runtime_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{runtime_root / 'test.db'}",
        auto_create_schema=True,
    )
    app_instance = create_app(settings)
    fake_runtime = StaticGameGenerationRuntime()
    app_instance.state.container.game_generation_runtime = fake_runtime
    app_instance.state.container.world_bootstrap_service._generation_runtime = fake_runtime
    try:
        yield app_instance
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)
