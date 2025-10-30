from pydantic import BaseModel
import pathlib


class ModelURLs(BaseModel):
    rvm: str
    retinaface: str
    bisenet: str
    dfl: str


DEFAULT_MODEL_URLS = ModelURLs(
    # Placeholder URLs; replace with real HF or storage links
    rvm="https://example.com/models/rvm.onnx",
    retinaface="https://example.com/models/retinaface_mnet.onnx",
    bisenet="https://example.com/models/bisenet.onnx",
    dfl="https://example.com/models/dfl.onnx",
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