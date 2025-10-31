from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
import cv2
import numpy as np
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


@router.get("/frame")
def get_latest_frame(request: Request):
    """返回当前流水线的最新融合帧（JPEG）。若无帧则返回占位图。"""
    mgr = getattr(request.app.state, "manager", None)
    img = None
    if mgr:
        try:
            # 尝试取队列中最新的一帧（将队列清空，仅保留最后一项）
            last = None
            while True:
                last = mgr.q_out.get_nowait()
            # 不可达：循环结束在异常处
        except Exception:
            # 取不到更多则使用最后一次成功取到的帧
            try:
                img = last  # type: ignore[name-defined]
            except Exception:
                img = None

    if img is None:
        # 构造占位图（1280x720 黑底，白字）
        h, w = 720, 1280
        img = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(img, "No output frame", (60, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(img, "Start pipeline or enable local preview", (60, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

    ok, buf = cv2.imencode(".jpg", img)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    return Response(content=buf.tobytes(), media_type="image/jpeg")