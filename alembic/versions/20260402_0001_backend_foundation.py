"""backend foundation

Revision ID: 20260402_0001
Revises:
Create Date: 2026-04-02 00:00:00
"""
"""Step 1 后端骨架的初始迁移。"""

from collections.abc import Sequence

from alembic import op

from app.db.base import Base
from app.models import *  # noqa: F403

# revision identifiers, used by Alembic.
revision: str = "20260402_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建当前已确认的全部基础表。"""

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """回滚 Step 1 初始表结构。"""

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
