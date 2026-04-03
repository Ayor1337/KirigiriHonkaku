"""FastAPI 应用装配入口。"""

from contextlib import asynccontextmanager
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI

from app.ai.runtime import StubAiRuntime
from app.api.v1.router import api_router
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_db_engine, create_session_factory
from app.engine.service import GameEngine
from app.models import *  # noqa: F403
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.seeds.world import DefaultWorldSeedProvider
from app.services.world_bootstrap import WorldBootstrapService
from app.services.world_state import WorldStateService
from app.storage.file_storage import FileStorage


@dataclass
class AppContainer:
    """聚合应用运行时依赖，避免路由层直接拼装底层对象。"""

    settings: Settings
    file_storage: FileStorage
    game_engine: GameEngine
    ai_runtime: StubAiRuntime
    world_bootstrap_service: WorldBootstrapService
    world_state_service: WorldStateService
    uow_factory: Callable[[], SqlAlchemyUnitOfWork]
    db_engine: object


def build_container(settings: Settings) -> AppContainer:
    """按配置构建应用所需的核心依赖。"""

    db_engine = create_db_engine(settings)
    session_factory = create_session_factory(db_engine)
    file_storage = FileStorage(settings.resolved_data_root)
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    seed_provider = DefaultWorldSeedProvider()
    return AppContainer(
        settings=settings,
        file_storage=file_storage,
        game_engine=GameEngine(),
        ai_runtime=StubAiRuntime(),
        world_bootstrap_service=WorldBootstrapService(uow_factory, file_storage, seed_provider),
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

        container.file_storage.initialize()
        if container.settings.auto_create_schema:
            # 测试环境直接建表，真实环境通过 Alembic 迁移管理 schema。
            Base.metadata.create_all(bind=container.db_engine)
        yield
        container.db_engine.dispose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.container = container
    app.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()
