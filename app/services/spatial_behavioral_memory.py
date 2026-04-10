from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class GridCellStats:
    row: int
    col: int
    movement_frequency: int
    mean_direction: tuple[float, float]


class SpatialBehavioralMemory:
    """Grid-based movement memory and anomaly detection for camera streams.

    The class tracks movement frequency and average flow direction per grid cell,
    then compares the current flow distribution with historical behavior using a
    z-score style coefficient normalized to [0.0, 1.0].
    """

    def __init__(
        self,
        grid_rows: int = 4,
        grid_cols: int = 4,
        movement_threshold: float = 0.8,
        zscore_scale: float = 3.0,
        history_learning_rate: float = 0.05,
        base_alert_threshold: float = 0.65,
        threshold_scale: float = 1.5,
        threshold_window: int = 50,
    ) -> None:
        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError("grid_rows and grid_cols must be > 0")
        if movement_threshold <= 0:
            raise ValueError("movement_threshold must be > 0")
        if zscore_scale <= 0:
            raise ValueError("zscore_scale must be > 0")
        if not (0 < history_learning_rate <= 1):
            raise ValueError("history_learning_rate must be in (0, 1]")
        if not (0 <= base_alert_threshold <= 1):
            raise ValueError("base_alert_threshold must be in [0, 1]")
        if threshold_scale < 0:
            raise ValueError("threshold_scale must be >= 0")
        if threshold_window <= 1:
            raise ValueError("threshold_window must be > 1")

        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.movement_threshold = movement_threshold
        self.zscore_scale = zscore_scale
        self.history_learning_rate = history_learning_rate
        self.base_alert_threshold = base_alert_threshold
        self.threshold_scale = threshold_scale
        self.threshold_window = threshold_window

        self._prev_gray: np.ndarray | None = None
        self._frame_shape: tuple[int, int] | None = None

        self._movement_frequency = np.zeros((grid_rows, grid_cols), dtype=np.int64)
        self._direction_sum = np.zeros((grid_rows, grid_cols, 2), dtype=np.float64)

        self._hist_mean: np.ndarray | None = None
        self._hist_var: np.ndarray | None = None
        self._coefficient_history: deque[float] = deque(maxlen=threshold_window)

    def process_frame(self, frame_bgr: np.ndarray) -> dict[str, object]:
        """Process one BGR frame and return anomaly metrics plus alert state."""
        if frame_bgr is None or frame_bgr.size == 0:
            raise ValueError("frame_bgr must be a non-empty BGR image")

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        if self._frame_shape is None:
            self._frame_shape = (h, w)
        elif self._frame_shape != (h, w):
            raise ValueError("All frames must have the same shape")

        if self._prev_gray is None:
            self._prev_gray = gray
            return {
                "anomaly_coefficient": 0.0,
                "threshold": self.dynamic_threshold,
                "alert": False,
                "cell_stats": self.get_cell_stats(),
            }

        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray,
            gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )
        self._prev_gray = gray

        current_distribution = self._grid_flow_distribution(flow)
        anomaly = self._compute_anomaly_coefficient(current_distribution)
        self._coefficient_history.append(anomaly)
        threshold = self.dynamic_threshold
        alert = anomaly > threshold

        self._update_behavior_memory(flow)
        self._update_historical_distribution(current_distribution)

        return {
            "anomaly_coefficient": anomaly,
            "threshold": threshold,
            "alert": alert,
            "cell_stats": self.get_cell_stats(),
        }

    @property
    def dynamic_threshold(self) -> float:
        if len(self._coefficient_history) < 2:
            return self.base_alert_threshold

        coeff_std = float(np.std(np.asarray(self._coefficient_history, dtype=np.float64)))
        threshold = self.base_alert_threshold + self.threshold_scale * coeff_std
        return float(np.clip(threshold, 0.0, 1.0))

    def get_cell_stats(self) -> list[GridCellStats]:
        stats: list[GridCellStats] = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                freq = int(self._movement_frequency[row, col])
                if freq > 0:
                    mean_dir = self._direction_sum[row, col] / freq
                    mean_tuple = (float(mean_dir[0]), float(mean_dir[1]))
                else:
                    mean_tuple = (0.0, 0.0)
                stats.append(
                    GridCellStats(
                        row=row,
                        col=col,
                        movement_frequency=freq,
                        mean_direction=mean_tuple,
                    )
                )
        return stats

    def _grid_flow_distribution(self, flow: np.ndarray) -> np.ndarray:
        h, w = flow.shape[:2]
        row_edges = np.linspace(0, h, self.grid_rows + 1, dtype=np.int32)
        col_edges = np.linspace(0, w, self.grid_cols + 1, dtype=np.int32)

        counts = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float64)
        magnitude = np.linalg.norm(flow, axis=2)

        for row in range(self.grid_rows):
            r0, r1 = row_edges[row], row_edges[row + 1]
            for col in range(self.grid_cols):
                c0, c1 = col_edges[col], col_edges[col + 1]
                cell_mag = magnitude[r0:r1, c0:c1]
                counts[row, col] = float(np.sum(cell_mag > self.movement_threshold))

        total = float(np.sum(counts))
        if total == 0:
            return np.zeros(self.grid_rows * self.grid_cols, dtype=np.float64)
        return (counts / total).reshape(-1)

    def _update_behavior_memory(self, flow: np.ndarray) -> None:
        h, w = flow.shape[:2]
        row_edges = np.linspace(0, h, self.grid_rows + 1, dtype=np.int32)
        col_edges = np.linspace(0, w, self.grid_cols + 1, dtype=np.int32)

        magnitude = np.linalg.norm(flow, axis=2)
        moving_mask = magnitude > self.movement_threshold

        for row in range(self.grid_rows):
            r0, r1 = row_edges[row], row_edges[row + 1]
            for col in range(self.grid_cols):
                c0, c1 = col_edges[col], col_edges[col + 1]
                cell_mask = moving_mask[r0:r1, c0:c1]
                movement_count = int(np.sum(cell_mask))
                if movement_count == 0:
                    continue

                cell_flow = flow[r0:r1, c0:c1][cell_mask]
                direction_mean = np.mean(cell_flow, axis=0)

                self._movement_frequency[row, col] += movement_count
                self._direction_sum[row, col] += direction_mean * movement_count

    def _compute_anomaly_coefficient(self, current_distribution: np.ndarray) -> float:
        if self._hist_mean is None or self._hist_var is None:
            return 0.0

        std = np.sqrt(np.maximum(self._hist_var, 1e-8))
        z_scores = np.abs((current_distribution - self._hist_mean) / std)

        z_mean = float(np.mean(z_scores))
        coefficient = z_mean / self.zscore_scale
        return float(np.clip(coefficient, 0.0, 1.0))

    def _update_historical_distribution(self, current_distribution: np.ndarray) -> None:
        if self._hist_mean is None:
            self._hist_mean = current_distribution.astype(np.float64)
            self._hist_var = np.full_like(self._hist_mean, 1e-4, dtype=np.float64)
            return

        alpha = self.history_learning_rate
        delta = current_distribution - self._hist_mean
        new_mean = (1.0 - alpha) * self._hist_mean + alpha * current_distribution

        # Exponential moving variance update for stable online z-score behavior.
        new_var = (1.0 - alpha) * self._hist_var + alpha * np.square(delta)

        self._hist_mean = new_mean
        self._hist_var = np.maximum(new_var, 1e-8)
