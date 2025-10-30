from dataclasses import dataclass
from typing import Any, List, Tuple


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    score: float


class FaceDetector:
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        # TODO: load ONNX RetinaFace model via onnxruntime-gpu

    def detect(self, frame) -> List[Detection]:
        # TODO: implement detection + tracking optimization
        return []