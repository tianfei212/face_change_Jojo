from fastapi import FastAPI

from .config import settings
from .utils import download_models


def register_startup_events(app: FastAPI):
    @app.on_event("startup")
    async def on_startup():
        # Trigger model auto download (F-FILE-AUTO)
        url_pairs = [
            ("rvm.onnx", settings.model_urls.rvm),
            ("retinaface_mnet.onnx", settings.model_urls.retinaface),
            ("bisenet.onnx", settings.model_urls.bisenet),
            ("dfl.onnx", settings.model_urls.dfl),
        ]
        try:
            download_models(url_pairs)
            app.state.status["models_ready"] = True
        except Exception as e:
            app.state.status.update({"state": "ERROR", "error": str(e), "models_ready": False})