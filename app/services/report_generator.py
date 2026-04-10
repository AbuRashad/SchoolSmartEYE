from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

import numpy as np


@dataclass(frozen=True)
class DailySSIRecord:
    date: date
    ssi_score: float


@dataclass(frozen=True)
class HeatmapRiskRecord:
    date: date
    location_id: str
    risk_intensity: float


class ReportGenerator:
    """Contribution 11: Institutional Self-Assessment report generator."""

    def __init__(self, national_standard_ssi: float = 75.0) -> None:
        if not (0.0 <= national_standard_ssi <= 100.0):
            raise ValueError("national_standard_ssi must be in [0.0, 100.0]")
        self.national_standard_ssi = national_standard_ssi

    def generate_semester_summary_report(
        self,
        school_name: str,
        semester_name: str,
        daily_ssi_scores: list[DailySSIRecord],
        heatmap_trends: list[HeatmapRiskRecord],
    ) -> dict[str, object]:
        if not daily_ssi_scores:
            raise ValueError("daily_ssi_scores must not be empty")

        avg_ssi = self.calculate_average_ssi(daily_ssi_scores)
        national_gap = avg_ssi - self.national_standard_ssi
        performance_label = self._performance_label(avg_ssi)

        top_risk_locations = self.top_risk_locations(heatmap_trends, top_k=3)
        recommendations = self.generate_improvement_recommendations(top_risk_locations)

        trend_summary = self._risk_trend_summary(heatmap_trends)

        return {
            "report_type": "semester_summary",
            "format": "json",
            "ministerial_review": {
                "ready": True,
                "sections": [
                    "institution_profile",
                    "safety_performance",
                    "national_benchmark_comparison",
                    "risk_hotspots",
                    "improvement_recommendations",
                ],
            },
            "institution_profile": {
                "school_name": school_name,
                "semester": semester_name,
                "national_standard_ssi": self.national_standard_ssi,
            },
            "safety_performance": {
                "average_ssi": avg_ssi,
                "performance_label": performance_label,
                "total_days_evaluated": len(daily_ssi_scores),
            },
            "national_benchmark_comparison": {
                "average_ssi": avg_ssi,
                "national_standard_ssi": self.national_standard_ssi,
                "gap": round(national_gap, 2),
                "status": "above_standard" if national_gap >= 0 else "below_standard",
            },
            "risk_hotspots": {
                "top_3_locations": top_risk_locations,
                "trend_summary": trend_summary,
            },
            "improvement_recommendations": recommendations,
        }

    @staticmethod
    def calculate_average_ssi(daily_ssi_scores: list[DailySSIRecord]) -> float:
        if not daily_ssi_scores:
            raise ValueError("daily_ssi_scores must not be empty")

        values = np.array([record.ssi_score for record in daily_ssi_scores], dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("SSI scores must be finite numeric values")

        values = np.clip(values, 0.0, 100.0)
        return float(np.round(np.mean(values), 2))

    @staticmethod
    def top_risk_locations(heatmap_trends: list[HeatmapRiskRecord], top_k: int = 3) -> list[dict[str, object]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if not heatmap_trends:
            return []

        grouped: dict[str, list[float]] = defaultdict(list)
        for entry in heatmap_trends:
            grouped[entry.location_id].append(float(np.clip(entry.risk_intensity, 0.0, 1.0)))

        ranked = sorted(
            grouped.items(),
            key=lambda item: (np.mean(item[1]), len(item[1])),
            reverse=True,
        )

        return [
            {
                "location_id": location,
                "average_risk": round(float(np.mean(values)), 4),
                "occurrences": len(values),
            }
            for location, values in ranked[:top_k]
        ]

    @staticmethod
    def generate_improvement_recommendations(top_risk_locations: list[dict[str, object]]) -> list[dict[str, str]]:
        recommendations: list[dict[str, str]] = []
        for rank, location in enumerate(top_risk_locations, start=1):
            location_id = str(location["location_id"])
            recommendations.append(
                {
                    "priority": f"P{rank}",
                    "location_id": location_id,
                    "action": (
                        f"Increase supervision density and stagger movement in {location_id}; "
                        "validate camera coverage and apply targeted behavioral interventions."
                    ),
                }
            )
        return recommendations

    @staticmethod
    def _risk_trend_summary(heatmap_trends: list[HeatmapRiskRecord]) -> dict[str, object]:
        if not heatmap_trends:
            return {"days_covered": 0, "most_frequent_risk_location": None}

        days_covered = len({record.date for record in heatmap_trends})
        location_counter = Counter(record.location_id for record in heatmap_trends)
        most_common = location_counter.most_common(1)[0][0]
        return {
            "days_covered": days_covered,
            "most_frequent_risk_location": most_common,
        }

    @staticmethod
    def to_pdf_structure(report_json: dict[str, object]) -> dict[str, object]:
        """Return a PDF-ready structure that can be rendered by a downstream engine."""
        return {
            "format": "pdf",
            "template": "ministerial_semester_summary_v1",
            "title": "Semester School Safety Self-Assessment",
            "content": report_json,
            "ready": True,
        }

    @staticmethod
    def _performance_label(avg_ssi: float) -> str:
        if avg_ssi >= 90:
            return "excellent"
        if avg_ssi >= 80:
            return "good"
        if avg_ssi >= 70:
            return "needs_improvement"
        return "critical_attention"
