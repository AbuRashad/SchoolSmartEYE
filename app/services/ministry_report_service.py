from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import numpy as np


@dataclass(frozen=True)
class SSIDailyScore:
    date: date
    score: float


@dataclass(frozen=True)
class RiskZoneRecord:
    date: date
    zone_id: str
    risk_intensity: float


class MinistryReportService:
    """Contribution 11 + Unit 11: ministry-level periodic reporting service."""

    def __init__(
        self,
        required_benchmark_ssi: float = 75.0,
        at_band_tolerance: float = 2.0,
    ) -> None:
        if not (0.0 <= required_benchmark_ssi <= 100.0):
            raise ValueError("required_benchmark_ssi must be in [0, 100]")
        if at_band_tolerance < 0:
            raise ValueError("at_band_tolerance must be >= 0")

        self.required_benchmark_ssi = required_benchmark_ssi
        self.at_band_tolerance = at_band_tolerance

    def generate_ministerial_summary(
        self,
        school_id: str,
        school_name: str,
        period_label: str,
        ssi_daily_scores: list[SSIDailyScore],
        heatmap_risk_records: list[RiskZoneRecord],
        scalability_level: str = "standard",
    ) -> dict[str, object]:
        if not ssi_daily_scores:
            raise ValueError("ssi_daily_scores must not be empty")
        if scalability_level not in {"minimum", "standard", "extended"}:
            raise ValueError("scalability_level must be one of: minimum, standard, extended")

        semester_ssi = self._average_ssi(ssi_daily_scores)
        benchmark_status = self._benchmark_status(semester_ssi)
        trend = self._ssi_trend(ssi_daily_scores)
        top_5_zones = self._top_risk_zones(heatmap_risk_records, top_k=5)
        development_plan = self._development_plan(top_5_zones)

        summary: dict[str, object] = {
            "report_type": "ministerial_summary",
            "format": "json",
            "school": {
                "school_id": school_id,
                "school_name": school_name,
                "period": period_label,
            },
            "overall_ssi_trend": trend,
            "semester_ssi_index": semester_ssi,
            "benchmark": {
                "required_ssi": self.required_benchmark_ssi,
                "status": benchmark_status,
                "difference": round(semester_ssi - self.required_benchmark_ssi, 2),
            },
            "top_5_recurring_risk_zones": top_5_zones,
            "development_plan": development_plan,
            "scalability_transfer_model": {
                "level": scalability_level,
                "available_levels": ["minimum", "standard", "extended"],
            },
            "governance_compliance": {
                "model": "Arab Data Governance Model",
                "contains_minor_video_frames": False,
                "aggregated_only": True,
                "pii_included": False,
            },
        }

        if scalability_level in {"standard", "extended"}:
            summary["summary_metrics"] = {
                "days_covered": len(ssi_daily_scores),
                "zones_considered": len({record.zone_id for record in heatmap_risk_records}),
            }

        if scalability_level == "extended":
            summary["extended_analytics"] = {
                "top_zone_average_risk": top_5_zones[0]["average_risk"] if top_5_zones else 0.0,
                "trend_slope_hint": trend["direction"],
            }

        return summary

    @staticmethod
    def to_pdf_payload(report_json: dict[str, object]) -> dict[str, object]:
        return {
            "format": "pdf",
            "template": "national_ministry_summary_v1",
            "ready": True,
            "content": report_json,
        }

    @staticmethod
    def _average_ssi(ssi_daily_scores: list[SSIDailyScore]) -> float:
        values = np.array([item.score for item in ssi_daily_scores], dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("SSI values must be finite")
        values = np.clip(values, 0.0, 100.0)
        return float(np.round(np.mean(values), 2))

    def _benchmark_status(self, semester_ssi: float) -> str:
        delta = semester_ssi - self.required_benchmark_ssi
        if abs(delta) <= self.at_band_tolerance:
            return "At"
        if delta > 0:
            return "Above"
        return "Below"

    @staticmethod
    def _ssi_trend(ssi_daily_scores: list[SSIDailyScore]) -> dict[str, object]:
        sorted_scores = sorted(ssi_daily_scores, key=lambda item: item.date)
        values = np.array([item.score for item in sorted_scores], dtype=np.float64)
        x = np.arange(len(values), dtype=np.float64)

        if len(values) == 1:
            slope = 0.0
        else:
            slope = float(np.polyfit(x, values, deg=1)[0])

        if slope > 0.15:
            direction = "improving"
        elif slope < -0.15:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "slope": round(slope, 4),
            "start_ssi": round(float(values[0]), 2),
            "end_ssi": round(float(values[-1]), 2),
        }

    @staticmethod
    def _top_risk_zones(records: list[RiskZoneRecord], top_k: int) -> list[dict[str, object]]:
        if not records:
            return []

        grouped: dict[str, list[float]] = defaultdict(list)
        for item in records:
            grouped[item.zone_id].append(float(np.clip(item.risk_intensity, 0.0, 1.0)))

        ranked = sorted(
            grouped.items(),
            key=lambda kv: (float(np.mean(kv[1])), len(kv[1])),
            reverse=True,
        )

        output: list[dict[str, object]] = []
        for zone, values in ranked[:top_k]:
            output.append(
                {
                    "zone_id": zone,
                    "average_risk": round(float(np.mean(values)), 4),
                    "occurrences": len(values),
                }
            )
        return output

    @staticmethod
    def _development_plan(top_5_zones: list[dict[str, object]]) -> list[dict[str, str]]:
        plan: list[dict[str, str]] = []
        for idx, zone in enumerate(top_5_zones, start=1):
            zone_id = str(zone["zone_id"])
            plan.append(
                {
                    "priority": f"P{idx}",
                    "zone_id": zone_id,
                    "recommendation": (
                        f"Deploy targeted supervision and crowd-flow redesign in {zone_id}; "
                        "audit schedule overlap and increase preventive monitoring."
                    ),
                }
            )
        return plan
