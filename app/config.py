from pydantic import BaseModel


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


class Settings(BaseModel):
    model_urls: ModelURLs = DEFAULT_MODEL_URLS
    models_dir: str = "/opt/fusion_assets/models"


settings = Settings()