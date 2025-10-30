from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..processing.manager import ProcessingManager, PipelineConfig


router = APIRouter()


class StreamStartRequest(BaseModel):
    use_multi_gpu: bool = True
    input_source: dict


@router.post("/start")
def start_stream(request: Request, body: StreamStartRequest):
    status = request.app.state.status
    if not status.get("models_ready", False):
        raise HTTPException(status_code=503, detail="Models not ready")

    if request.app.state.manager:
        raise HTTPException(status_code=409, detail="Stream already running")

    cfg = PipelineConfig(use_multi_gpu=body.use_multi_gpu, input_source=body.input_source)
    request.app.state.manager = ProcessingManager(cfg)
    request.app.state.manager.start()
    request.app.state.status.update({"state": "PROCESSING", "error": None})
    return {"ok": True}


@router.post("/stop")
def stop_stream(request: Request):
    if not request.app.state.manager:
        return {"ok": True}
    request.app.state.manager.stop()
    request.app.state.manager = None
    request.app.state.status.update({"state": "IDLE", "error": None})
    return {"ok": True}


@router.get("/status")
def stream_status(request: Request):
    return request.app.state.status