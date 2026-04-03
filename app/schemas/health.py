"""健康检查 schema。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查返回值。"""

    status: str = "ok"
