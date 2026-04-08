"""V1 版本路由聚合入口。"""

from fastapi import APIRouter

from app.api.v1.routes import actions, board, health, sessions


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(board.router, tags=["board"])
api_router.include_router(actions.router, tags=["actions"])
