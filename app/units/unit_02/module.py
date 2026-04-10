"""Unit 02: Scene Understanding Unit — تقدير الكثافة واتجاهات الحركة ومناطق التكدس."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

UNIT_02_NAME = "Scene Understanding Unit"


@dataclass(frozen=True)
class SceneSnapshot:
    location_id: str
    captured_at: datetime
    crowd_density: float          # [0,1] normalized
    dominant_direction: tuple[float, float]  # (dx, dy) unit vector
    congestion_zones: tuple[str, ...]
    movement_entropy: float       # [0,1] — high = chaotic movement
    person_count_estimate: int


class SceneUnderstandingUnit:
    """Estimates crowd density, movement directions, and congestion zones from frame flow data."""

    _CONGESTION_THRESHOLD = 0.70
    _ENTROPY_BINS = 8

    def __init__(self, grid_rows: int = 4, grid_cols: int = 4) -> None:
        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError("grid_rows and grid_cols must be > 0")
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self._zone_labels: dict[tuple[int, int], str] = {}

    def label_zone(self, row: int, col: int, label: str) -> None:
        self._zone_labels[(row, col)] = label

    def analyze(
        self,
        flow: np.ndarray,
        density_map: np.ndarray,
        location_id: str,
        captured_at: datetime | None = None,
    ) -> SceneSnapshot:
        """Derive scene metrics from optical flow and a density grid."""
        if flow.ndim != 3 or flow.shape[2] != 2:
            raise ValueError("flow must be an (H, W, 2) array")
        if density_map.shape != (self.grid_rows, self.grid_cols):
            raise ValueError("density_map shape does not match grid configuration")

        density_map = np.clip(density_map.astype(np.float32), 0.0, 1.0)
        crowd_density = float(np.mean(density_map))

        magnitude = np.linalg.norm(flow, axis=2)
        moving_mask = magnitude > 0.5
        if np.any(moving_mask):
            mean_flow = np.mean(flow[moving_mask], axis=0)
            norm = float(np.linalg.norm(mean_flow))
            dominant_dir: tuple[float, float] = (
                float(mean_flow[0] / norm) if norm > 0 else 0.0,
                float(mean_flow[1] / norm) if norm > 0 else 0.0,
            )
        else:
            dominant_dir = (0.0, 0.0)

        congestion: list[str] = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                if density_map[row, col] >= self._CONGESTION_THRESHOLD:
                    label = self._zone_labels.get((row, col), f"Zone({row},{col})")
                    congestion.append(label)

        # Movement entropy via angle histogram
        angles = np.arctan2(flow[moving_mask, 1], flow[moving_mask, 0]) if np.any(moving_mask) else np.array([])
        if angles.size > 0:
            hist, _ = np.histogram(angles, bins=self._ENTROPY_BINS, range=(-np.pi, np.pi), density=True)
            hist = hist[hist > 0]
            bin_w = 2 * np.pi / self._ENTROPY_BINS
            entropy = float(-np.sum(hist * np.log(hist + 1e-9) * bin_w))
            max_entropy = float(np.log(self._ENTROPY_BINS))
            movement_entropy = float(np.clip(entropy / max_entropy, 0.0, 1.0)) if max_entropy > 0 else 0.0
        else:
            movement_entropy = 0.0

        pixel_area = flow.shape[0] * flow.shape[1]
        person_count_estimate = max(0, int(crowd_density * pixel_area / 400))

        return SceneSnapshot(
            location_id=location_id,
            captured_at=captured_at or datetime.utcnow(),
            crowd_density=crowd_density,
            dominant_direction=dominant_dir,
            congestion_zones=tuple(congestion),
            movement_entropy=movement_entropy,
            person_count_estimate=person_count_estimate,
        )
