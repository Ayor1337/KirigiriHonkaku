"""统一动作入口。"""

import json
from datetime import datetime, timezone

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
        if session.status != "ready":
            raise HTTPException(status_code=409, detail="Session world state has not been bootstrapped.")

        engine_result = container.game_engine.process(payload, session, uow)
        ai_result = container.ai_runtime.run(engine_result)
        history_path = container.file_storage.write_session_history(
            session.uuid,
            "latest_action.json",
            json.dumps(
                {
                    "action_type": payload.action_type,
                    "status": engine_result.status,
                    "current_time_minute": session.current_time_minute,
                    "generated_text": ai_result.generated_text,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        uow.commit()
        return ActionResult(
            status=engine_result.status,
            action_type=payload.action_type,
            state_delta_summary=engine_result.state_delta_summary,
            scene_snapshot=engine_result.scene_snapshot,
            ai_tasks=engine_result.ai_tasks,
            soft_state_patch=ai_result.soft_state_patch,
            storage_refs={"latest_action_log": history_path},
            errors=engine_result.errors,
        )
