"""会话创建与查询接口。"""

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.session import CreateSessionRequest, SessionResponse


router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: CreateSessionRequest, request: Request) -> SessionResponse:
    """创建最小会话骨架，并初始化会话对应的运行时目录。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.create(payload)
        directories = container.file_storage.create_session_tree(session.uuid)
        session.story_file_path = f"{directories['story']}\\STORY.md"
        session.history_file_path = f"{directories['history']}\\HISTORY.md"
        session.truth_file_path = f"{directories['truth']}\\TRUTH.md"
        uow.commit()
        response = SessionResponse.model_validate(session, from_attributes=True)
        response.data_directories = directories
        return response


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, request: Request) -> SessionResponse:
    """读取现有会话的基础状态和目录信息。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        directories = container.file_storage.create_session_tree(session.uuid)
        response = SessionResponse.model_validate(session, from_attributes=True)
        response.data_directories = directories
        return response
