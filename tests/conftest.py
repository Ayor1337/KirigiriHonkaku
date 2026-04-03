import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def app():
    runtime_root = Path("tests_runtime") / uuid4().hex
    runtime_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{runtime_root / 'test.db'}",
        data_root=runtime_root / "data",
        auto_create_schema=True,
    )
    try:
        yield create_app(settings)
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)
