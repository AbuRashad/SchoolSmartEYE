from datetime import date

import pytest

from app.services.report_generator import DailySSIRecord, HeatmapRiskRecord, ReportGenerator


def test_report_calculates_average_safety_score_over_period() -> None:
    generator = ReportGenerator(national_standard_ssi=75.0)
    daily_scores = [
        DailySSIRecord(date=date(2026, 1, 1), ssi_score=80.0),
        DailySSIRecord(date=date(2026, 1, 2), ssi_score=70.0),
        DailySSIRecord(date=date(2026, 1, 3), ssi_score=90.0),
    ]

    report = generator.generate_semester_summary_report(
        school_name="Al Noor School",
        semester_name="Spring 2026",
        daily_ssi_scores=daily_scores,
        heatmap_trends=[],
    )

    assert report["safety_performance"]["average_ssi"] == pytest.approx(80.0)


def test_report_identifies_top_3_risk_locations() -> None:
    generator = ReportGenerator(national_standard_ssi=75.0)
    daily_scores = [DailySSIRecord(date=date(2026, 2, 1), ssi_score=78.0)]

    trends = [
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Gate", risk_intensity=0.9),
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Gate", risk_intensity=0.8),
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Playground", risk_intensity=0.85),
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Playground", risk_intensity=0.8),
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Corridor-B", risk_intensity=0.75),
        HeatmapRiskRecord(date=date(2026, 2, 1), location_id="Classroom-A", risk_intensity=0.2),
    ]

    report = generator.generate_semester_summary_report(
        school_name="Al Noor School",
        semester_name="Spring 2026",
        daily_ssi_scores=daily_scores,
        heatmap_trends=trends,
    )

    top_3 = report["risk_hotspots"]["top_3_locations"]
    assert len(top_3) == 3
    assert [item["location_id"] for item in top_3] == ["Gate", "Playground", "Corridor-B"]


def test_report_format_is_ready_for_ministerial_review() -> None:
    generator = ReportGenerator(national_standard_ssi=75.0)
    daily_scores = [DailySSIRecord(date=date(2026, 3, 1), ssi_score=82.0)]

    report = generator.generate_semester_summary_report(
        school_name="Al Noor School",
        semester_name="Spring 2026",
        daily_ssi_scores=daily_scores,
        heatmap_trends=[],
    )

    assert report["format"] == "json"
    assert report["ministerial_review"]["ready"] is True
    assert "safety_performance" in report
    assert "national_benchmark_comparison" in report
    assert "improvement_recommendations" in report

    pdf_payload = generator.to_pdf_structure(report)
    assert pdf_payload["format"] == "pdf"
    assert pdf_payload["ready"] is True
    assert pdf_payload["content"]["report_type"] == "semester_summary"
