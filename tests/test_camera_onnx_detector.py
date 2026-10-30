from pathlib import Path

import numpy as np
import pytest

from app.services.camera_onnx_detector import OnnxPersonObjectDetector


class Meta:
    def __init__(self, name, shape):
        self.name, self.shape = name, shape


class FakeSession:
    def __init__(self, output, shape=(1, 3, 100, 200)):
        self.output = output
        self.shape = shape
        self.feed = None

    def get_inputs(self):
        return [Meta("images", self.shape)]

    def get_outputs(self):
        return [Meta("detections", None)]

    def run(self, names, feed):
        self.feed = feed
        return [self.output]


@pytest.fixture
def model_file(tmp_path):
    path = tmp_path / "fixture.onnx"
    path.write_bytes(b"test-placeholder-not-a-real-model")
    return path


def test_post_nms_output_maps_boxes_to_original_frame(model_file):
    session = FakeSession(np.array([[[20, 10, 100, 80, .9, 0]]], dtype=np.float32))
    detector = OnnxPersonObjectDetector(
        model_file, {0: "person"}, input_width=200, input_height=100,
        session=session, model_version="fixture-v1",
    )
    result = detector.detect(np.zeros((200, 400, 3), dtype=np.uint8))
    assert len(result) == 1
    assert (result[0].x1, result[0].y1, result[0].x2, result[0].y2) == (40, 20, 200, 160)
    assert result[0].label == "person"
    assert session.feed["images"].shape == (1, 3, 100, 200)


def test_filters_low_confidence_and_unknown_classes(model_file):
    output = np.array([[0, 0, 20, 20, .2, 0], [0, 0, 20, 20, .9, 9]], dtype=np.float32)
    detector = OnnxPersonObjectDetector(model_file, {0: "person"},
        input_width=200, input_height=100, session=FakeSession(output))
    assert detector.detect(np.zeros((100, 200, 3), dtype=np.uint8)) == []


def test_rejects_unsupported_output_shape(model_file):
    detector = OnnxPersonObjectDetector(model_file, {0: "person"},
        input_width=200, input_height=100, session=FakeSession(np.zeros((1, 84, 8400))))
    with pytest.raises(ValueError, match="shape"):
        detector.detect(np.zeros((100, 200, 3), dtype=np.uint8))


def test_rejects_model_input_dimension_mismatch(model_file):
    with pytest.raises(ValueError, match="input_width"):
        OnnxPersonObjectDetector(model_file, {0: "person"},
            input_width=100, input_height=100, session=FakeSession(np.zeros((1, 0, 6))))


def test_requires_existing_model_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        OnnxPersonObjectDetector(tmp_path / "missing.onnx", {0: "person"},
            input_width=200, input_height=100, session=FakeSession(np.zeros((0, 6))))
