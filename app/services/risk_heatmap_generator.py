from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class Timeframe:
    start: datetime
    end: datetime


class RiskHeatmapGenerator:
    """Contribution 6: Spatio-Temporal Risk Heatmap generator.

    This service fuses risk signals from:
    - SBM anomaly coefficients per grid cell
    - Predictive density risk per grid cell
    and returns a frontend-ready JSON structure containing (x, y, time_slot,
    risk_intensity) where risk_intensity is normalized to [0.0, 1.0].
    """

    def __init__(
        self,
        grid_rows: int,
        grid_cols: int,
        anomaly_weight: float = 0.6,
        density_weight: float = 0.4,
    ) -> None:
        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError("grid_rows and grid_cols must be greater than zero")
        if anomaly_weight < 0 or density_weight < 0:
            raise ValueError("anomaly_weight and density_weight must be non-negative")
        if anomaly_weight + density_weight <= 0:
            raise ValueError("At least one fusion weight must be greater than zero")

        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        total = anomaly_weight + density_weight
        self.anomaly_weight = anomaly_weight / total
        self.density_weight = density_weight / total

        self._sbm_risk: dict[str, dict[datetime, np.ndarray]] = {}
        self._density_risk: dict[str, dict[datetime, np.ndarray]] = {}

    def ingest_sbm_anomaly(self, location_id: str, time_slot: datetime, anomaly_grid: np.ndarray) -> None:
        self._validate_grid(anomaly_grid)
        self._sbm_risk.setdefault(location_id, {})[time_slot] = np.clip(
            anomaly_grid.astype(np.float32), 0.0, 1.0
        )

    def ingest_predictive_density(self, location_id: str, time_slot: datetime, density_grid: np.ndarray) -> None:
        self._validate_grid(density_grid)
        self._density_risk.setdefault(location_id, {})[time_slot] = np.clip(
            density_grid.astype(np.float32), 0.0, 1.0
        )

    def generate_heatmap_data(self, location_id: str, timeframe: Timeframe) -> dict[str, object]:
        """Return weighted spatio-temporal heatmap JSON for frontend overlays."""
        if timeframe.start > timeframe.end:
            raise ValueError("timeframe.start must be <= timeframe.end")

        sbm_slots = self._sbm_risk.get(location_id, {})
        density_slots = self._density_risk.get(location_id, {})
        all_slots = sorted(set(sbm_slots.keys()) | set(density_slots.keys()))

        selected_slots = [slot for slot in all_slots if timeframe.start <= slot <= timeframe.end]

        cells: list[dict[str, object]] = []
        for slot in selected_slots:
            anomaly = sbm_slots.get(slot, np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32))
            density = density_slots.get(slot, np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32))

            fused = np.clip(
                self.anomaly_weight * anomaly + self.density_weight * density,
                0.0,
                1.0,
            )

            for y in range(self.grid_rows):
                for x in range(self.grid_cols):
                    cells.append(
                        {
                            "x": x,
                            "y": y,
                            "time_slot": slot.isoformat(),
                            "risk_intensity": float(fused[y, x]),
                        }
                    )

        return {
            "location_id": location_id,
            "timeframe": {
                "start": timeframe.start.isoformat(),
                "end": timeframe.end.isoformat(),
            },
            "grid": {"rows": self.grid_rows, "cols": self.grid_cols},
            "cells": cells,
        }

    def _validate_grid(self, grid: np.ndarray) -> None:
        arr = np.asarray(grid)
        if arr.shape != (self.grid_rows, self.grid_cols):
            raise ValueError("Risk grid shape does not match configured generator grid")
