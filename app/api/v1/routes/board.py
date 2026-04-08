from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.board import BoardSaveRequest, SessionBoardResponse
from app.services.board import BoardService, BoardSessionNotFoundError, BoardValidationError, DetectiveBoardNotFoundError


router = APIRouter()


@router.get("/sessions/{session_id}/board", response_model=SessionBoardResponse)
def get_session_board(session_id: str, request: Request) -> SessionBoardResponse:
    """读取当前会话的侦探板。"""

    service: BoardService = request.app.state.container.board_service
    try:
        return service.get_board(session_id)
    except BoardSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except DetectiveBoardNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found for session.") from exc


@router.put("/sessions/{session_id}/board", response_model=SessionBoardResponse)
def save_session_board(session_id: str, payload: BoardSaveRequest, request: Request) -> SessionBoardResponse:
    """整板覆盖保存当前会话的侦探板。"""

    service: BoardService = request.app.state.container.board_service
    try:
        return service.save_board(session_id, payload)
    except BoardSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except DetectiveBoardNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found for session.") from exc
    except BoardValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

