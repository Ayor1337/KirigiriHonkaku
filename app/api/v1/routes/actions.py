"""统一动作入口。"""

from fastapi import APIRouter, HTTPException, Request

from app.schemas.action import ActionRequest, ActionResult


router = APIRouter()


@router.post("/actions", response_model=ActionResult)
def submit_action(payload: ActionRequest, request: Request) -> ActionResult:
    """接收统一 Action，请求引擎结算并串接 AI Runtime 与存储层。"""

    container = request.app.state.container
    with container.uow_factory() as uow:
        session = uow.sessions.get(payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.status == "draft":
            raise HTTPException(status_code=409, detail="Session world state has not been bootstrapped.")
        if session.status == "generating":
            raise HTTPException(status_code=409, detail="Session world state is currently being generated.")
        if session.status == "ended":
            raise HTTPException(status_code=409, detail="Session has already ended.")

        engine_result = container.game_engine.process(payload, session, uow)
        narrative_result = container.narrative_service.run(payload, session, engine_result, uow)
        uow.commit()
        return ActionResult(
            status=engine_result.status,
            action_type=payload.action_type,
            state_delta_summary=engine_result.state_delta_summary,
            scene_snapshot=engine_result.scene_snapshot,
            ai_tasks=engine_result.ai_tasks,
            soft_state_patch=narrative_result.soft_state_patch,
            narrative_text=narrative_result.narrative_text,
            storage_refs=narrative_result.storage_refs,
            errors=engine_result.errors,
        )
