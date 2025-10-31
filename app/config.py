from pydantic import BaseModel
import os
import pathlib


class ModelURLs(BaseModel):
    rvm: str
    retinaface: str
    bisenet: str
    dfl: str


DEFAULT_MODEL_URLS = ModelURLs(
    # 可通过环境变量覆盖，便于自动下载真实模型地址
    # 如：MODEL_URL_RVM, MODEL_URL_RETINAFACE, MODEL_URL_BISENET, MODEL_URL_DFL
    rvm=os.getenv("MODEL_URL_RVM", "https://example.com/models/rvm.onnx"),
    retinaface=os.getenv("MODEL_URL_RETINAFACE", "https://example.com/models/retinaface_mnet.onnx"),
    bisenet=os.getenv("MODEL_URL_BISENET", "https://example.com/models/bisenet.onnx"),
    dfl=os.getenv("MODEL_URL_DFL", "https://example.com/models/dfl.onnx"),
)


BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = ASSETS_DIR / "models"


class Settings(BaseModel):
    model_urls: ModelURLs = DEFAULT_MODEL_URLS
    models_dir: str = str(MODELS_DIR)
    debug: bool = True
    log_level: str = "DEBUG"


settings = Settings()