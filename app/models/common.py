"""模型层通用 mixin。"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """返回 UTC 当前时间。"""

    return datetime.now(timezone.utc)


class IdMixin:
    """提供 UUID 主键。"""

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)


class AuditMixin:
    """提供 created_at / updated_at 审计字段。"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class UpdatedAtMixin:
    """提供仅包含 updated_at 的轻量时间字段。"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
