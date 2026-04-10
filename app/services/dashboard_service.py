from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from app.services.risk_heatmap_generator import RiskHeatmapGenerator, Timeframe
from app.services.school_safety_index import compute_school_safety_index_with_forecast
from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityObservation


def _build_seeded_forecaster() -> CrowdDensityForecaster:
    rng = np.random.default_rng(42)
    observations: list[DensityObservation] = []
    for hour in range(7, 15):
        for minute in [0, 15, 30, 45]:
            ts = datetime(2026, 4, 6, hour, minute)
            t = hour * 60 + minute
            base = 0.30 + 0.30 * float(np.exp(-((t - 480) ** 2) / 900))
            base += 0.25 * float(np.exp(-((t - 720) ** 2) / 400))
            observations.append(DensityObservation(
                location="main-campus",
                timestamp=ts,
                density=float(np.clip(base + rng.normal(0, 0.04), 0, 1)),
            ))
    fc = CrowdDensityForecaster(safety_threshold=0.75, default_horizon_minutes=15)
    fc.fit(observations)
    return fc


class DashboardService:
    """Frontend-facing dashboard aggregation service."""

    def __init__(self) -> None:
        self.school_name = "Smart School Safety System"
        self.benchmark = 75
        self._forecaster = _build_seeded_forecaster()

    def _compute_live_ssi(self) -> tuple[int, object]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        ssi, density_pred = compute_school_safety_index_with_forecast(
            anomaly_coefficient=0.18,
            coherence_score=0.76,
            attendance_discrepancy=0.08,
            forecaster=self._forecaster,
            location="main-campus",
            current_time=now,
            coherence_represents_alignment=True,
        )
        return int(round(ssi)), density_pred

    def get_summary(self) -> dict[str, object]:
        ssi, _ = self._compute_live_ssi()
        return {
            "schoolName": self.school_name,
            "ssi": ssi,
            "benchmark": self.benchmark,
            "websocketStatus": "connected",
        }

    def get_alerts(self) -> list[dict[str, object]]:
        ssi, density_pred = self._compute_live_ssi()
        anomaly_coefficient = 0.35
        computed_at = datetime.now(timezone.utc).isoformat()
        alerts: list[dict[str, object]] = []

        if anomaly_coefficient > 0.3:
            alerts.append({
                "id": "alert-coherence",
                "title": "Coherence Rupture",
                "message": f"Behavioral anomaly coefficient {anomaly_coefficient:.2f} exceeds safety threshold. Motion synchrony fragmented.",
                "severity": "critical",
                "stream": "coherence",
                "computed_at": computed_at,
            })

        if anomaly_coefficient > 0.1:
            alerts.append({
                "id": "alert-anomaly",
                "title": "Anomaly Coefficient",
                "message": f"Anomaly coefficient {anomaly_coefficient:.2f} elevated above morning baseline.",
                "severity": "warning",
                "stream": "anomaly",
                "computed_at": computed_at,
            })

        if density_pred.warning:
            alerts.append({
                "id": "alert-density",
                "title": "High Crowd Density",
                "message": f"Predicted density {density_pred.predicted_density:.2f} exceeds safety threshold {density_pred.safety_threshold}.",
                "severity": "critical",
                "stream": "density",
                "computed_at": computed_at,
            })

        if ssi < self.benchmark and not any(a["id"] == "alert-anomaly" for a in alerts):
            alerts.append({
                "id": "alert-ssi",
                "title": "SSI Below Benchmark",
                "message": f"School Safety Index {ssi} is below benchmark {self.benchmark}.",
                "severity": "warning",
                "stream": "anomaly",
                "computed_at": computed_at,
            })

        if not alerts:
            alerts.append({
                "id": "alert-stable",
                "title": "Density Stable",
                "message": "All indicators within normal operational bounds.",
                "severity": "stable",
                "stream": "density",
                "computed_at": computed_at,
            })

        return alerts

    def get_heatmap(self) -> dict[str, object]:
        now = datetime(2026, 4, 6, 7, 30)
        prediction = now + timedelta(minutes=15)

        generator = RiskHeatmapGenerator(grid_rows=2, grid_cols=2, anomaly_weight=0.6, density_weight=0.4)
        generator.ingest_sbm_anomaly(
            "main-campus", now,
            np.array([[0.88, 0.44], [0.26, 0.31]], dtype=np.float32),
        )
        generator.ingest_predictive_density(
            "main-campus", now,
            np.array([[0.82, 0.31], [0.21, 0.29]], dtype=np.float32),
        )
        generator.ingest_sbm_anomaly(
            "main-campus", prediction,
            np.array([[0.32, 0.56], [0.28, 0.77]], dtype=np.float32),
        )
        generator.ingest_predictive_density(
            "main-campus", prediction,
            np.array([[0.70, 0.57], [0.41, 0.98]], dtype=np.float32),
        )

        raw = generator.generate_heatmap_data(
            location_id="main-campus",
            timeframe=Timeframe(start=now, end=prediction),
        )

        label_map = {
            (0, 0): "Main Gate",
            (1, 0): "Corridor A",
            (0, 1): "Learning Commons",
            (1, 1): "Playground",
        }

        cells: list[dict[str, object]] = []
        for cell in raw["cells"]:
            slot = cell["time_slot"]
            view = "live" if slot == now.isoformat() else "prediction_15m"
            cells.append({
                "x": cell["x"],
                "y": cell["y"],
                "time_slot": view,
                "risk_intensity": cell["risk_intensity"],
                "reason": self._reason_for_cell(cell["x"], cell["y"], view),
                "label": label_map[(cell["x"], cell["y"])],
            })

        return {
            "location_id": raw["location_id"],
            "availableTimeSlots": ["live", "prediction_15m"],
            "cells": cells,
        }

    def get_snapshot(self) -> dict[str, object]:
        summary = self.get_summary()
        summary["liveAlerts"] = self.get_alerts()
        heatmap = self.get_heatmap()
        summary["heatmapCells"] = heatmap["cells"]
        summary["availableTimeSlots"] = heatmap["availableTimeSlots"]
        summary["fetchedFromBackend"] = True
        return summary

    @staticmethod
    def _reason_for_cell(x: int, y: int, view: str) -> str:
        reason_map = {
            (0, 0, "live"): "Behavioral Anomaly",
            (1, 0, "live"): "Anomaly Coefficient",
            (0, 1, "live"): "Normal Flow",
            (1, 1, "live"): "Normal Flow",
            (0, 0, "prediction_15m"): "Predicted High Density",
            (1, 0, "prediction_15m"): "Behavioral Anomaly",
            (0, 1, "prediction_15m"): "Normal Flow",
            (1, 1, "prediction_15m"): "Predicted High Density",
        }
        return reason_map[(x, y, view)]
