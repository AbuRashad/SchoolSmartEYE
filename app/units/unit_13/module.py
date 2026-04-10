"""Unit 13: Institutional Self-Assessment — وحدة التقييم الذاتي المؤسسي (تقرير نهاية الفصل)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

UNIT_13_NAME = "Institutional Self-Assessment Unit"


@dataclass(frozen=True)
class SemesterAssessmentReport:
    school_id: str
    school_name: str
    semester_label: str
    average_ssi: float
    peak_ssi: float
    trough_ssi: float
    ssi_trend: str            # "improving" | "stable" | "declining"
    top_hazard_zones: tuple[str, ...]
    drill_completion_rate: float   # [0,1]
    recommendations: tuple[str, ...]
    generated_on: date


class InstitutionalSelfAssessmentUnit:
    """Generates end-of-semester self-assessment report for school leadership."""

    BENCHMARK = 75.0

    def generate(
        self,
        school_id: str,
        school_name: str,
        semester_label: str,
        daily_ssi_scores: list[float],
        hazard_zone_counts: dict[str, int],
        drills_scheduled: int,
        drills_completed: int,
        generated_on: date | None = None,
    ) -> SemesterAssessmentReport:
        if not daily_ssi_scores:
            raise ValueError("daily_ssi_scores must not be empty")
        if drills_scheduled < 0 or drills_completed < 0:
            raise ValueError("drill counts must be non-negative")

        arr = np.array(daily_ssi_scores, dtype=np.float64)
        avg = float(np.mean(arr))
        peak = float(np.max(arr))
        trough = float(np.min(arr))

        # Trend: compare first-half vs second-half mean
        mid = len(arr) // 2
        first_half = float(np.mean(arr[:mid])) if mid > 0 else avg
        second_half = float(np.mean(arr[mid:])) if mid < len(arr) else avg
        if second_half > first_half + 2:
            trend = "improving"
        elif second_half < first_half - 2:
            trend = "declining"
        else:
            trend = "stable"

        top_zones = sorted(hazard_zone_counts, key=hazard_zone_counts.get, reverse=True)[:3]  # type: ignore[arg-type]

        drill_rate = drills_completed / max(drills_scheduled, 1)

        recommendations = self._build_recommendations(avg, trend, drill_rate, top_zones)

        return SemesterAssessmentReport(
            school_id=school_id,
            school_name=school_name,
            semester_label=semester_label,
            average_ssi=round(avg, 2),
            peak_ssi=round(peak, 2),
            trough_ssi=round(trough, 2),
            ssi_trend=trend,
            top_hazard_zones=tuple(top_zones),
            drill_completion_rate=round(drill_rate, 4),
            recommendations=tuple(recommendations),
            generated_on=generated_on or date.today(),
        )

    def _build_recommendations(
        self,
        avg: float,
        trend: str,
        drill_rate: float,
        top_zones: list[str],
    ) -> list[str]:
        recs: list[str] = []
        if avg < self.BENCHMARK:
            recs.append(
                f"Overall SSI ({avg:.1f}) is below the national benchmark ({self.BENCHMARK}). "
                "A targeted safety improvement plan is recommended."
            )
        if trend == "declining":
            recs.append("SSI trend is declining. An urgent review of safety protocols is advised.")
        if drill_rate < 0.80:
            recs.append(
                f"Drill completion rate is {drill_rate:.0%}. "
                "Schedule remaining drills before the end of term."
            )
        for zone in top_zones:
            recs.append(f"Zone '{zone}' registered the highest hazard frequency. Consider physical review.")
        if not recs:
            recs.append("Safety performance is within acceptable parameters. Continue current protocols.")
        return recs
