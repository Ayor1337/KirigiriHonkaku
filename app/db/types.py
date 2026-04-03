"""跨数据库兼容的类型别名。"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


# PostgreSQL 使用 JSONB，测试期 sqlite 回退到通用 JSON。
JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")
