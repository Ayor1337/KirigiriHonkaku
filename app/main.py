"""FastAPI 应用装配入口。"""

from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from app.ai.game_generation import GameGenerationRuntime, create_game_generation_runtime
from app.ai.runtime import NarrativeRuntime, create_narrative_runtime
from app.api.v1.router import api_router
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_db_engine, create_session_factory
from app.engine.service import GameEngine
from app.models import *  # noqa: F403
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.board import BoardService
from app.services.narrative import NarrativeService
from app.services.world_bootstrap import WorldBootstrapService
from app.services.world_state import WorldStateService
from app.storage.file_storage import FileStorage


@dataclass
class AppContainer:
    """聚合应用运行时依赖，避免路由层直接拼装底层对象。"""

    settings: Settings
    game_engine: GameEngine
    ai_runtime: NarrativeRuntime
    game_generation_runtime: GameGenerationRuntime
    narrative_service: NarrativeService
    board_service: BoardService
    world_bootstrap_service: WorldBootstrapService
    world_state_service: WorldStateService
    uow_factory: Callable[[], SqlAlchemyUnitOfWork]
    db_engine: object


def build_container(settings: Settings) -> AppContainer:
    """按配置构建应用所需的核心依赖。"""

    db_engine = create_db_engine(settings)
    session_factory = create_session_factory(db_engine)
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    ai_runtime = create_narrative_runtime(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout_seconds=settings.openai_timeout_seconds,
    )
    game_generation_runtime = create_game_generation_runtime(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout_seconds=settings.openai_game_generation_timeout_seconds,
    )
    narrative_service = NarrativeService(ai_runtime)
    return AppContainer(
        settings=settings,
        game_engine=GameEngine(),
        ai_runtime=ai_runtime,
        game_generation_runtime=game_generation_runtime,
        narrative_service=narrative_service,
        board_service=BoardService(uow_factory),
        world_bootstrap_service=WorldBootstrapService(uow_factory, game_generation_runtime),
        world_state_service=WorldStateService(uow_factory),
        uow_factory=uow_factory,
        db_engine=db_engine,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""

    app_settings = settings or Settings()
    container = build_container(app_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """负责应用启动和关闭时的基础资源管理。"""

        if container.settings.auto_create_schema:
            Base.metadata.create_all(bind=container.db_engine)
        yield
        container.db_engine.dispose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.container = container
    app.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()
