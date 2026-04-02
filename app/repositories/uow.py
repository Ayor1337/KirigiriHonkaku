"""Unit of Work 实现。"""

from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.session_repository import SessionRepository


class SqlAlchemyUnitOfWork:
    """为一次应用请求封装事务与仓库访问入口。"""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory
        self.session: Session | None = None
        self.sessions: SessionRepository | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        """打开事务作用域并初始化仓库。"""

        self.session = self._session_factory()
        self.sessions = SessionRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """在异常时回滚，在退出时关闭会话。"""

        if self.session is None:
            return
        if exc_type:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        """提交当前事务。"""

        if self.session is None:
            raise RuntimeError("UnitOfWork session has not been opened.")
        self.session.commit()

    def rollback(self) -> None:
        """显式回滚当前事务。"""

        if self.session is None:
            return
        self.session.rollback()


UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
