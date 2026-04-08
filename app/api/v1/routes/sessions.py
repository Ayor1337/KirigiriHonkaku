"""会话创建与查询接口。"""

import json
from queue import Queue
from threading import Thread
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.ai.game_generation import (
    GameGenerationBlueprintValidationError,
    GameGenerationOutputError,
    GameGenerationProviderError,
)
from app.schemas.session import (
    SessionBootstrapErrorEvent,
    SessionBootstrapResponse,
    SessionBootstrapStageEvent,
    SessionDialogueDetailResponse,
    SessionDialogueSummaryResponse,
    SessionDialogueUtteranceResponse,
    SessionMapResponse,
    SessionNpcResponse,
    SessionPlayerResponse,
    SessionResponse,
    SessionStateResponse,
    SessionSummaryResponse,
)
from app.services.world_bootstrap import (
    SessionAlreadyBootstrappedError,
    SessionGenerationInProgressError,
    SessionNotFoundError,
)


router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(request: Request) -> SessionResponse:
    """创建最小会话骨架。"""

    container = request.app.state.container
    draft = container.world_bootstrap_service.create_draft_session()
    with container.uow_factory() as uow:
        session = uow.sessions.get(draft.session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Session creation failed.")
        return SessionResponse.model_validate(session, from_attributes=True)


@router.post("/bootstrap-stream")

def bootstrap_session_world_stream(request: Request) -> StreamingResponse:
    """创建会话并以 SSE 形式实时返回世界生成阶段。"""

    container = request.app.state.container
    event_queue: Queue[str | None] = Queue()
    stream_state: dict[str, str | None] = {"session_id": None, "last_placeholder": None}

    def emit_stage(placeholder: str, metadata: dict[str, Any]) -> None:
        """把服务层进度事件转成 SSE stage 事件并入队。"""

        payload = dict(metadata)
        session_id = payload.get("session_id") or stream_state["session_id"]
        if session_id is not None:
            payload["session_id"] = str(session_id)
            stream_state["session_id"] = str(session_id)
        stream_state["last_placeholder"] = placeholder
        stage_event = SessionBootstrapStageEvent.model_validate({"placeholder": placeholder, **payload})
        event_queue.put(_format_sse("stage", stage_event.model_dump(exclude_none=True)))

    def worker() -> None:
        """在后台线程中执行 bootstrap，避免阻塞主请求线程。"""

        try:
            result = container.world_bootstrap_service.create_and_bootstrap(progress_callback=emit_stage)
            complete_event = SessionBootstrapResponse(
                session_id=result.session_id,
                status=result.status,
                created_counts=result.created_counts,
                root_ids=result.root_ids,
            )
            event_queue.put(_format_sse("complete", complete_event.model_dump()))
        except Exception as exc:
            error_event = _build_stream_error(
                exc,
                session_id=stream_state["session_id"],
                failed_placeholder=stream_state["last_placeholder"],
            )
            event_queue.put(_format_sse("error", error_event.model_dump(exclude_none=True)))
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()

    def event_stream():
        """持续消费队列并按 SSE 协议向客户端推送事件。"""

        while True:
            item = event_queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/bootstrap", response_model=SessionBootstrapResponse)
def bootstrap_session_world(session_id: str, request: Request) -> SessionBootstrapResponse:
    """为指定会话生成完整可玩的世界状态。"""

    container = request.app.state.container
    try:
        result = container.world_bootstrap_service.bootstrap(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except SessionAlreadyBootstrappedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session world state has already been bootstrapped.",
        ) from exc
    except SessionGenerationInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session world state is currently being generated.",
        ) from exc
    except GameGenerationBlueprintValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Generated world blueprint failed validation.", "errors": exc.errors},
        ) from exc
    except GameGenerationOutputError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except GameGenerationProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return SessionBootstrapResponse(
        session_id=result.session_id,
        status=result.status,
        created_counts=result.created_counts,
        root_ids=result.root_ids,
    )


@router.get("", response_model=list[SessionSummaryResponse])
def list_sessions(request: Request) -> list[SessionSummaryResponse]:
    """读取全部会话的基础状态列表。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        return [SessionSummaryResponse.model_validate(item, from_attributes=True) for item in uow.sessions.list_all()]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, request: Request) -> SessionResponse:
    """读取现有会话的基础状态和根对象 ID。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        root_ids: dict[str, str] = {}
        player = uow.players.get_by_session(session_id)
        game_map = uow.maps.get_by_session(session_id)
        if player is not None:
            root_ids["player_id"] = str(player.id)
        if game_map is not None:
            root_ids["map_id"] = str(game_map.id)

        return SessionResponse(
            id=session.id,
            uuid=session.uuid,
            title=session.title,
            status=session.status,
            start_time_minute=session.start_time_minute,
            current_time_minute=session.current_time_minute,
            story_markdown=session.story_markdown,
            root_ids=root_ids,
        )


@router.get("/{session_id}/state", response_model=SessionStateResponse)
def get_session_state(session_id: str, request: Request) -> SessionStateResponse:
    """读取现有会话的状态详情。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return SessionStateResponse(
            exposure_value=session.exposure_value,
            exposure_level=session.exposure_level,
        )


@router.get("/{session_id}/player", response_model=SessionPlayerResponse)
def get_session_player(session_id: str, request: Request) -> SessionPlayerResponse:
    """读取现有会话的玩家详情。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        player = uow.players.get_by_session(session_id)
        if player is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found for session.")

        current_location = player.character.current_location
        player_state = player.state
        return SessionPlayerResponse(
            id=player.id,
            character_id=player.character_id,
            display_name=player.character.display_name,
            public_identity=player.character.public_identity,
            template_key=player.template_key,
            template_name=player.template_name,
            trait_text=player.trait_text,
            background_text=player.background_text,
            current_location_id=current_location.id if current_location is not None else None,
            current_location_name=current_location.name if current_location is not None else None,
            exposure_value=player_state.exposure_value if player_state is not None else session.exposure_value,
            exposure_level=player_state.exposure_level if player_state is not None else session.exposure_level,
        )


@router.get("/{session_id}/npcs", response_model=list[SessionNpcResponse])
def get_session_npcs(session_id: str, request: Request) -> list[SessionNpcResponse]:
    """读取当前会话中所有已见过面的 NPC。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        npcs = []
        for npc in uow.npcs.list_by_session(session_id):
            if npc.state is None or not npc.state.has_met_player:
                continue
            current_location = npc.state.current_location
            npcs.append(
                SessionNpcResponse(
                    id=npc.id,
                    character_id=npc.character_id,
                    template_key=npc.template_key,
                    display_name=npc.character.display_name,
                    public_identity=npc.character.public_identity,
                    current_location_id=current_location.id if current_location is not None else None,
                    current_location_name=current_location.name if current_location is not None else None,
                    has_met_player=True,
                )
            )
        return npcs


@router.get("/{session_id}/dialogues", response_model=list[SessionDialogueSummaryResponse])
def get_session_dialogues(session_id: str, request: Request) -> list[SessionDialogueSummaryResponse]:
    """读取当前会话中的聊天会话列表。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        dialogues = sorted(
            uow.dialogues.list_by_session(session_id),
            key=lambda item: (item.end_minute or item.start_minute, item.created_at),
            reverse=True,
        )
        npcs_by_character_id = {str(npc.character_id): npc for npc in uow.npcs.list_by_session(session_id)}
        return [_build_dialogue_summary(dialogue, npcs_by_character_id) for dialogue in dialogues]


@router.get("/{session_id}/dialogues/{dialogue_id}", response_model=SessionDialogueDetailResponse)
def get_session_dialogue_detail(session_id: str, dialogue_id: str, request: Request) -> SessionDialogueDetailResponse:
    """读取单个聊天会话详情。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        dialogue = uow.dialogues.get_by_session_and_id(session_id, dialogue_id)
        if dialogue is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialogue not found for session.")

        npcs_by_character_id = {str(npc.character_id): npc for npc in uow.npcs.list_by_session(session_id)}
        summary = _build_dialogue_summary(dialogue, npcs_by_character_id)
        return SessionDialogueDetailResponse(
            **summary.model_dump(),
            tag_flags=dict(dialogue.tag_flags or {}),
            utterances=[
                SessionDialogueUtteranceResponse(
                    sequence_no=utterance.sequence_no,
                    speaker_role=_resolve_speaker_role(utterance, npcs_by_character_id),
                    speaker_name=utterance.speaker_character.display_name,
                    content=utterance.content,
                    tone_tag=utterance.tone_tag,
                    utterance_flags=dict(utterance.utterance_flags or {}),
                )
                for utterance in dialogue.utterances
            ],
        )


@router.get("/{session_id}/map", response_model=SessionMapResponse)
def get_session_map(session_id: str, request: Request) -> SessionMapResponse:
    """读取现有会话的地图详情。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        game_map = uow.maps.get_by_session(session_id)
        if game_map is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found for session.")

        return SessionMapResponse(
            id=game_map.id,
            template_key=game_map.template_key,
            display_name=game_map.display_name,
            locations=[
                {
                    "id": location.id,
                    "key": location.key,
                    "parent_location_id": location.parent_location_id,
                    "name": location.name,
                    "description": location.description,
                    "location_type": location.location_type,
                    "visibility_level": location.visibility_level,
                    "is_hidden": location.is_hidden,
                    "status_flags": dict(location.status_flags or {}),
                }
                for location in sorted(game_map.locations, key=lambda item: item.key)
            ],
            connections=[
                {
                    "id": connection.id,
                    "from_location_id": connection.from_location_id,
                    "to_location_id": connection.to_location_id,
                    "connection_type": connection.connection_type,
                    "access_rule": dict(connection.access_rule or {}),
                    "is_hidden": connection.is_hidden,
                    "is_locked": connection.is_locked,
                    "is_one_way": connection.is_one_way,
                    "is_dangerous": connection.is_dangerous,
                    "time_window_rule": dict(connection.time_window_rule or {}),
                }
                for connection in sorted(
                    game_map.connections,
                    key=lambda item: (
                        item.from_location.key,
                        item.to_location.key,
                        item.connection_type or "",
                        str(item.id),
                    ),
                )
            ],
        )


def _build_dialogue_summary(dialogue, npcs_by_character_id: dict[str, Any]) -> SessionDialogueSummaryResponse:
    """把对话聚合压缩成列表页所需的最小摘要结构。"""

    target_npc = _resolve_target_npc(dialogue, npcs_by_character_id)
    last_utterance = dialogue.utterances[-1] if dialogue.utterances else None
    location = dialogue.location
    return SessionDialogueSummaryResponse(
        dialogue_id=dialogue.id,
        target_npc_key=target_npc.template_key if target_npc is not None else None,
        target_npc_name=target_npc.character.display_name if target_npc is not None else None,
        location_id=location.id if location is not None else None,
        location_key=location.key if location is not None else None,
        location_name=location.name if location is not None else None,
        start_minute=dialogue.start_minute,
        end_minute=dialogue.end_minute,
        utterance_count=len(dialogue.utterances),
        last_utterance_preview=last_utterance.content if last_utterance is not None else None,
    )


def _resolve_target_npc(dialogue, npcs_by_character_id: dict[str, Any]):
    """从参与者列表里解析出非玩家的目标 NPC。"""

    for participant in dialogue.participants:
        if participant.character.kind == "player":
            continue
        npc = npcs_by_character_id.get(str(participant.character_id))
        if npc is not None:
            return npc
    return None


def _resolve_speaker_role(utterance, npcs_by_character_id: dict[str, Any]) -> str:
    """根据说话者角色和 NPC 索引推导统一的发言身份标签。"""

    if utterance.speaker_character.kind == "player":
        return "player"
    return "npc" if str(utterance.speaker_character_id) in npcs_by_character_id else "unknown"



def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    """把事件名和 JSON 负载编码成标准 SSE 文本块。"""

    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_stream_error(
    exc: Exception,
    *,
    session_id: str | None,
    failed_placeholder: str | None,
) -> SessionBootstrapErrorEvent:
    """把领域异常映射为前端可消费的流式错误事件。"""

    if isinstance(exc, SessionNotFoundError):
        return SessionBootstrapErrorEvent(
            code="session_not_found",
            message="Session not found.",
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    if isinstance(exc, SessionAlreadyBootstrappedError):
        return SessionBootstrapErrorEvent(
            code="already_bootstrapped",
            message="Session world state has already been bootstrapped.",
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    if isinstance(exc, SessionGenerationInProgressError):
        return SessionBootstrapErrorEvent(
            code="generation_in_progress",
            message="Session world state is currently being generated.",
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    if isinstance(exc, GameGenerationBlueprintValidationError):
        return SessionBootstrapErrorEvent(
            code="generation_failed",
            message="Generated world blueprint failed validation.",
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    if isinstance(exc, GameGenerationOutputError):
        return SessionBootstrapErrorEvent(
            code="generation_output_invalid",
            message=str(exc),
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    if isinstance(exc, GameGenerationProviderError):
        return SessionBootstrapErrorEvent(
            code="generation_provider_error",
            message=str(exc),
            session_id=session_id,
            failed_placeholder=failed_placeholder,
        )
    return SessionBootstrapErrorEvent(
        code="internal_error",
        message=str(exc) or exc.__class__.__name__,
        session_id=session_id,
        failed_placeholder=failed_placeholder,
    )
