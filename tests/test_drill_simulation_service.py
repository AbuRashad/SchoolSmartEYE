from datetime import datetime

import pytest

from app.services.crowd_density_forecasting import DensityObservation
from app.services.drill_simulation_service import (
    DrillSimulationService,
    LayoutCell,
    SupervisorResponse,
)
from app.services.spatial_behavioral_memory import GridCellStats


def test_system_builds_scenario_from_actual_layout_data() -> None:
    service = DrillSimulationService(expected_response_seconds=120.0)
    layout = [
        LayoutCell(x=0, y=0, zone_id="Classroom-A"),
        LayoutCell(x=1, y=0, zone_id="Main-Gate", is_exit=True, is_high_capacity=True),
        LayoutCell(x=0, y=1, zone_id="Playground", is_high_capacity=True),
        LayoutCell(x=1, y=1, zone_id="Corridor-A"),
    ]
    movement = [
        GridCellStats(row=0, col=0, movement_frequency=10, mean_direction=(0.1, 0.1)),
        GridCellStats(row=0, col=1, movement_frequency=85, mean_direction=(1.0, 0.2)),
        GridCellStats(row=1, col=0, movement_frequency=60, mean_direction=(0.8, 0.1)),
    ]
    density = [
        DensityObservation(location="Main-Gate", timestamp=datetime(2026, 4, 6, 7, 30), density=0.9),
        DensityObservation(location="Playground", timestamp=datetime(2026, 4, 6, 10, 0), density=0.7),
    ]

    scenario = service.create_virtual_risk_scenario(
        scenario_type="stampede",
        layout_cells=layout,
        movement_patterns=movement,
        density_observations=density,
        created_at=datetime(2026, 4, 6, 12, 0),
    )

    assert scenario.trigger_zone == "Main-Gate"
    assert "Main-Gate" in scenario.affected_zones
    assert "Main-Gate" in scenario.predicted_bottlenecks
    assert 0.0 <= scenario.risk_level <= 1.0


def test_response_score_calculates_correctly_for_supervisor_interaction() -> None:
    service = DrillSimulationService(expected_response_seconds=120.0)
    response = SupervisorResponse(
        supervisor_id="sup-01",
        response_time_seconds=60.0,
        protocol_steps_completed=4,
        protocol_steps_total=5,
    )

    score = service.calculate_effectiveness_score(response)

    expected = 100.0 * (0.6 * (4 / 5) + 0.4 * (1.0 - 60.0 / 120.0))
    assert score == pytest.approx(expected)


def test_simulation_data_is_stored_separately_from_real_operational_logs() -> None:
    service = DrillSimulationService(expected_response_seconds=120.0)
    service.real_operational_log.append({"type": "ssi_operational_record", "score": 88.0})

    layout = [LayoutCell(x=0, y=0, zone_id="Main-Gate", is_exit=True)]
    movement = [GridCellStats(row=0, col=0, movement_frequency=50, mean_direction=(1.0, 0.0))]
    density = [DensityObservation(location="Main-Gate", timestamp=datetime(2026, 4, 6, 7, 30), density=0.8)]

    scenario = service.create_virtual_risk_scenario(
        scenario_type="fire",
        layout_cells=layout,
        movement_patterns=movement,
        density_observations=density,
        created_at=datetime(2026, 4, 6, 12, 0),
    )
    response_record = service.record_supervisor_response(
        scenario,
        SupervisorResponse(
            supervisor_id="sup-02",
            response_time_seconds=30.0,
            protocol_steps_completed=3,
            protocol_steps_total=3,
        ),
    )
    report = service.generate_simulation_report(scenario, [response_record])

    assert all(entry.get("simulation_only", False) or entry.get("type") == "scenario" or entry.get("type") == "report" for entry in service.simulation_log)
    assert service.real_operational_log == [{"type": "ssi_operational_record", "score": 88.0}]
    assert report["simulation_only"] is True
    assert report["note"].lower().find("separately") != -1
