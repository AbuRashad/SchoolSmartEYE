from datetime import datetime

import pytest
import numpy as np

from app.services.risk_heatmap_generator import RiskHeatmapGenerator, Timeframe


def test_data_fusion_combines_anomaly_and_predicted_density() -> None:
    generator = RiskHeatmapGenerator(grid_rows=2, grid_cols=2, anomaly_weight=0.7, density_weight=0.3)
    slot = datetime(2026, 4, 6, 7, 30)

    anomaly = np.array([[0.9, 0.1], [0.2, 0.2]], dtype=np.float32)
    density = np.array([[0.8, 0.2], [0.1, 0.3]], dtype=np.float32)

    generator.ingest_sbm_anomaly("campus-a", slot, anomaly)
    generator.ingest_predictive_density("campus-a", slot, density)

    result = generator.generate_heatmap_data(
        location_id="campus-a",
        timeframe=Timeframe(start=slot, end=slot),
    )

    top_left = next(cell for cell in result["cells"] if cell["x"] == 0 and cell["y"] == 0)
    expected = 0.7 * 0.9 + 0.3 * 0.8
    assert top_left["risk_intensity"] == pytest.approx(expected)


def test_temporal_peak_shifts_by_time_of_day() -> None:
    generator = RiskHeatmapGenerator(grid_rows=2, grid_cols=2)
    gate_slot = datetime(2026, 4, 6, 7, 30)
    playground_slot = datetime(2026, 4, 6, 10, 0)

    gate_peak = np.array([[1.0, 0.1], [0.1, 0.1]], dtype=np.float32)
    playground_peak = np.array([[0.1, 0.1], [0.1, 1.0]], dtype=np.float32)

    generator.ingest_sbm_anomaly("campus-a", gate_slot, gate_peak)
    generator.ingest_predictive_density("campus-a", gate_slot, gate_peak)
    generator.ingest_sbm_anomaly("campus-a", playground_slot, playground_peak)
    generator.ingest_predictive_density("campus-a", playground_slot, playground_peak)

    result = generator.generate_heatmap_data(
        location_id="campus-a",
        timeframe=Timeframe(start=gate_slot, end=playground_slot),
    )

    gate_cells = [cell for cell in result["cells"] if cell["time_slot"] == gate_slot.isoformat()]
    play_cells = [cell for cell in result["cells"] if cell["time_slot"] == playground_slot.isoformat()]

    gate_max = max(gate_cells, key=lambda item: item["risk_intensity"])
    play_max = max(play_cells, key=lambda item: item["risk_intensity"])

    assert (gate_max["x"], gate_max["y"]) == (0, 0)
    assert (play_max["x"], play_max["y"]) == (1, 1)


def test_actionable_output_contains_full_coordinate_overlay_json() -> None:
    generator = RiskHeatmapGenerator(grid_rows=3, grid_cols=4)
    slot = datetime(2026, 4, 6, 11, 0)

    anomaly = np.full((3, 4), 0.4, dtype=np.float32)
    density = np.full((3, 4), 0.5, dtype=np.float32)
    generator.ingest_sbm_anomaly("campus-a", slot, anomaly)
    generator.ingest_predictive_density("campus-a", slot, density)

    result = generator.generate_heatmap_data(
        location_id="campus-a",
        timeframe=Timeframe(start=slot, end=slot),
    )

    assert result["location_id"] == "campus-a"
    assert result["grid"] == {"rows": 3, "cols": 4}
    assert len(result["cells"]) == 12

    coordinates = {(cell["x"], cell["y"]) for cell in result["cells"]}
    expected_coordinates = {(x, y) for y in range(3) for x in range(4)}

    assert coordinates == expected_coordinates
    assert all(0.0 <= cell["risk_intensity"] <= 1.0 for cell in result["cells"])
