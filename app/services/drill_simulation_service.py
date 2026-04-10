from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from app.services.crowd_density_forecasting import DensityObservation
from app.services.spatial_behavioral_memory import GridCellStats


@dataclass(frozen=True)
class LayoutCell:
    x: int
    y: int
    zone_id: str
    is_exit: bool = False
    is_high_capacity: bool = False


@dataclass(frozen=True)
class SupervisorResponse:
    supervisor_id: str
    response_time_seconds: float
    protocol_steps_completed: int
    protocol_steps_total: int


@dataclass(frozen=True)
class VirtualRiskScenario:
    scenario_id: str
    scenario_type: str
    created_at: datetime
    trigger_zone: str
    affected_zones: tuple[str, ...]
    predicted_bottlenecks: tuple[str, ...]
    risk_level: float
    layout_snapshot: tuple[LayoutCell, ...]


class DrillSimulationService:
    """Contribution 8: Safety Drill Simulation Module."""

    def __init__(self, expected_response_seconds: float = 120.0) -> None:
        if expected_response_seconds <= 0:
            raise ValueError("expected_response_seconds must be greater than zero")

        self.expected_response_seconds = expected_response_seconds
        self.simulation_log: list[dict[str, object]] = []
        self.real_operational_log: list[dict[str, object]] = []

    def create_virtual_risk_scenario(
        self,
        scenario_type: str,
        layout_cells: list[LayoutCell],
        movement_patterns: list[GridCellStats],
        density_observations: list[DensityObservation],
        created_at: datetime | None = None,
    ) -> VirtualRiskScenario:
        if not layout_cells:
            raise ValueError("layout_cells must not be empty")

        created_at = created_at or datetime.utcnow()
        zone_risk = self._zone_risk_scores(layout_cells, movement_patterns, density_observations)
        ranked_zones = sorted(zone_risk.items(), key=lambda item: item[1], reverse=True)

        trigger_zone = ranked_zones[0][0]
        affected_zones = tuple(zone for zone, _ in ranked_zones[: min(4, len(ranked_zones))])
        bottlenecks = tuple(zone for zone in affected_zones if self._zone_has_exit_or_capacity_flag(zone, layout_cells))
        risk_level = float(np.clip(np.mean([score for _, score in ranked_zones[: max(1, len(affected_zones))]]), 0.0, 1.0))

        scenario = VirtualRiskScenario(
            scenario_id=f"sim-{created_at.strftime('%Y%m%d%H%M%S')}",
            scenario_type=scenario_type,
            created_at=created_at,
            trigger_zone=trigger_zone,
            affected_zones=affected_zones,
            predicted_bottlenecks=bottlenecks,
            risk_level=risk_level,
            layout_snapshot=tuple(layout_cells),
        )
        self.simulation_log.append({"type": "scenario", "scenario": scenario})
        return scenario

    def calculate_effectiveness_score(self, response: SupervisorResponse) -> float:
        if response.response_time_seconds < 0:
            raise ValueError("response_time_seconds must be non-negative")
        if response.protocol_steps_total <= 0:
            raise ValueError("protocol_steps_total must be greater than zero")
        if response.protocol_steps_completed < 0:
            raise ValueError("protocol_steps_completed must be non-negative")

        protocol_ratio = min(response.protocol_steps_completed / response.protocol_steps_total, 1.0)
        response_ratio = 1.0 - min(response.response_time_seconds / self.expected_response_seconds, 1.0)
        score = 100.0 * (0.6 * protocol_ratio + 0.4 * response_ratio)
        return float(np.clip(round(score, 2), 0.0, 100.0))

    def record_supervisor_response(
        self,
        scenario: VirtualRiskScenario,
        response: SupervisorResponse,
    ) -> dict[str, object]:
        score = self.calculate_effectiveness_score(response)
        record = {
            "type": "response",
            "scenario_id": scenario.scenario_id,
            "scenario_type": scenario.scenario_type,
            "supervisor_id": response.supervisor_id,
            "effectiveness_score": score,
            "response_time_seconds": response.response_time_seconds,
            "protocol_adherence": round(
                min(response.protocol_steps_completed / response.protocol_steps_total, 1.0),
                4,
            ),
            "simulation_only": True,
        }
        self.simulation_log.append(record)
        return record

    def generate_simulation_report(
        self,
        scenario: VirtualRiskScenario,
        supervisor_records: list[dict[str, object]],
    ) -> dict[str, object]:
        avg_score = 0.0
        if supervisor_records:
            avg_score = float(np.mean([float(item["effectiveness_score"]) for item in supervisor_records]))

        report = {
            "report_type": "simulation_report",
            "scenario_id": scenario.scenario_id,
            "scenario_type": scenario.scenario_type,
            "created_at": scenario.created_at.isoformat(),
            "trigger_zone": scenario.trigger_zone,
            "affected_zones": list(scenario.affected_zones),
            "predicted_bottlenecks": list(scenario.predicted_bottlenecks),
            "risk_level": scenario.risk_level,
            "average_effectiveness_score": round(avg_score, 2),
            "supervisor_records": supervisor_records,
            "simulation_only": True,
            "note": "Simulation data is stored separately from operational SSI logs.",
        }
        self.simulation_log.append({"type": "report", "report": report})
        return report

    @staticmethod
    def _zone_has_exit_or_capacity_flag(zone_id: str, layout_cells: list[LayoutCell]) -> bool:
        return any(
            cell.zone_id == zone_id and (cell.is_exit or cell.is_high_capacity)
            for cell in layout_cells
        )

    @staticmethod
    def _zone_risk_scores(
        layout_cells: list[LayoutCell],
        movement_patterns: list[GridCellStats],
        density_observations: list[DensityObservation],
    ) -> dict[str, float]:
        zone_by_coord = {(cell.x, cell.y): cell.zone_id for cell in layout_cells}
        movement_by_zone: dict[str, list[float]] = {}
        for stat in movement_patterns:
            zone_id = zone_by_coord.get((stat.col, stat.row))
            if zone_id is None:
                continue
            vector_strength = float(np.linalg.norm(np.asarray(stat.mean_direction, dtype=np.float64)))
            score = min((stat.movement_frequency / 100.0) + vector_strength, 1.0)
            movement_by_zone.setdefault(zone_id, []).append(score)

        density_by_zone: dict[str, list[float]] = {}
        for observation in density_observations:
            density_by_zone.setdefault(observation.location, []).append(float(np.clip(observation.density, 0.0, 1.0)))

        all_zones = {cell.zone_id for cell in layout_cells}
        risk_scores: dict[str, float] = {}
        for zone in all_zones:
            movement_score = float(np.mean(movement_by_zone.get(zone, [0.0])))
            density_score = float(np.mean(density_by_zone.get(zone, [0.0])))
            risk_scores[zone] = float(np.clip(0.55 * movement_score + 0.45 * density_score, 0.0, 1.0))

        return risk_scores
