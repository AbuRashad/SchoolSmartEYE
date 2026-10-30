"""Optional local ONNX Runtime adapter with an explicit post-NMS output contract.

The adapter does not download models. It accepts only ONNX models whose single
output is rows of [x1, y1, x2, y2, confidence, class_id] in input-image pixels.
Coordinates are mapped back to the original frame after a direct resize.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol, Sequence
from math import isfinite

import cv2
import numpy as np

from app.services.camera_event_intelligence import ObjectDetection


class _Session(Protocol):
    def get_inputs(self): ...
    def get_outputs(self): ...
    def run(self, output_names, input_feed): ...


class OnnxRuntimeUnavailable(RuntimeError):
    """Raised when the optional ONNX Runtime package is not installed."""


class OnnxPersonObjectDetector:
    """CPU-only ONNX adapter for a documented [N,6] post-NMS model output."""

    def __init__(
        self,
        model_path: str | Path,
        labels: Mapping[int, str],
        *,
        input_width: int,
        input_height: int,
        confidence_threshold: float = 0.35,
        session: _Session | None = None,
        model_version: str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"ONNX model file does not exist: {self.model_path}")
        if not labels or any(not str(label).strip() for label in labels.values()):
            raise ValueError("labels must map class IDs to non-empty names")
        if input_width < 1 or input_height < 1:
            raise ValueError("input dimensions must be positive")
        if not isfinite(confidence_threshold) or not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        self.labels = {int(key): str(value) for key, value in labels.items()}
        self.input_width = int(input_width)
        self.input_height = int(input_height)
        self.confidence_threshold = float(confidence_threshold)

        if session is None:
            try:
                import onnxruntime as ort
            except ImportError as exc:
                raise OnnxRuntimeUnavailable(
                    "Install the optional CPU runtime with: pip install onnxruntime"
                ) from exc
            session = ort.InferenceSession(
                str(self.model_path), providers=["CPUExecutionProvider"]
            )
        self._session = session
        inputs, outputs = session.get_inputs(), session.get_outputs()
        if len(inputs) != 1 or len(outputs) != 1:
            raise ValueError("model must expose exactly one input and one output")
        self._input_name = inputs[0].name
        self._output_name = outputs[0].name
        shape = inputs[0].shape
        if len(shape) != 4 or shape[1] not in (3, "3"):
            raise ValueError("model input must use NCHW with 3 channels")
        if isinstance(shape[2], int) and shape[2] != self.input_height:
            raise ValueError("configured input_height does not match model input")
        if isinstance(shape[3], int) and shape[3] != self.input_width:
            raise ValueError("configured input_width does not match model input")
        self.model_version = model_version or f"onnx:{self.model_path.name}"

    def detect(self, frame: np.ndarray) -> Sequence[ObjectDetection]:
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            raise ValueError("frame must be a non-empty BGR color image")
        original_h, original_w = frame.shape[:2]
        resized = cv2.resize(frame, (self.input_width, self.input_height),
                             interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
        raw = np.asarray(self._session.run([self._output_name], {
            self._input_name: tensor
        })[0])
        if raw.ndim == 3 and raw.shape[0] == 1:
            raw = raw[0]
        if raw.ndim != 2 or raw.shape[1] != 6:
            raise ValueError("model output must have shape [N,6] or [1,N,6] with xyxy,score,class_id")
        scale_x, scale_y = original_w / self.input_width, original_h / self.input_height
        detections: list[ObjectDetection] = []
        for row in raw:
            x1, y1, x2, y2, score, class_value = (float(value) for value in row)
            if not all(isfinite(value) for value in (x1, y1, x2, y2, score, class_value)):
                raise ValueError("model output contains non-finite values")
            class_id = int(class_value)
            if class_value != class_id:
                raise ValueError("model class_id must be an integer")
            if class_id not in self.labels or score < self.confidence_threshold:
                continue
            x1, x2 = sorted((max(0.0, min(self.input_width, x1)),
                             max(0.0, min(self.input_width, x2))))
            y1, y2 = sorted((max(0.0, min(self.input_height, y1)),
                             max(0.0, min(self.input_height, y2))))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(ObjectDetection(
                self.labels[class_id], score, x1 * scale_x, y1 * scale_y,
                x2 * scale_x, y2 * scale_y,
            ))
        return detections
