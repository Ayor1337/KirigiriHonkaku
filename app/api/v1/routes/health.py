"""健康检查接口。"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    """返回进程级健康状态。"""

    return HealthResponse()
