import cv2
import numpy as np

from app.services.spatial_behavioral_memory import SpatialBehavioralMemory


def _make_translated_frame(base: np.ndarray, dx: int, dy: int) -> np.ndarray:
    h, w = base.shape[:2]
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(base, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return shifted


def test_initialization_and_first_frame_behavior() -> None:
    sbm = SpatialBehavioralMemory(grid_rows=3, grid_cols=5)
    frame = np.zeros((120, 200, 3), dtype=np.uint8)

    result = sbm.process_frame(frame)

    assert 0.0 <= result["anomaly_coefficient"] <= 1.0
    assert result["alert"] is False
    assert len(result["cell_stats"]) == 15


def test_anomaly_increases_with_directional_shift_and_triggers_alert() -> None:
    sbm = SpatialBehavioralMemory(
        grid_rows=4,
        grid_cols=4,
        movement_threshold=0.4,
        base_alert_threshold=0.05,
        threshold_scale=0.0,
        history_learning_rate=0.1,
    )

    rng = np.random.default_rng(7)
    base = (rng.random((120, 120, 3)) * 255).astype(np.uint8)

    sbm.process_frame(base)
    stable = sbm.process_frame(base)

    moved = _make_translated_frame(base, dx=10, dy=0)
    shifted = sbm.process_frame(moved)

    assert shifted["anomaly_coefficient"] >= stable["anomaly_coefficient"]
    assert 0.0 <= shifted["anomaly_coefficient"] <= 1.0
    assert shifted["alert"] is True

    total_frequency = sum(cell.movement_frequency for cell in shifted["cell_stats"])
    assert total_frequency > 0
