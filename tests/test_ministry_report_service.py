from datetime import date

from app.services.ministry_report_service import MinistryReportService, RiskZoneRecord, SSIDailyScore


def _sample_daily_scores() -> list[SSIDailyScore]:
    return [
        SSIDailyScore(date=date(2026, 1, 1), score=70.0),
        SSIDailyScore(date=date(2026, 1, 2), score=80.0),
        SSIDailyScore(date=date(2026, 1, 3), score=90.0),
    ]


def _sample_risk_records() -> list[RiskZoneRecord]:
    return [
        RiskZoneRecord(date=date(2026, 1, 1), zone_id="Gate", risk_intensity=0.92),
        RiskZoneRecord(date=date(2026, 1, 2), zone_id="Gate", risk_intensity=0.89),
        RiskZoneRecord(date=date(2026, 1, 1), zone_id="Playground", risk_intensity=0.81),
        RiskZoneRecord(date=date(2026, 1, 2), zone_id="Playground", risk_intensity=0.8),
        RiskZoneRecord(date=date(2026, 1, 1), zone_id="Corridor-A", risk_intensity=0.76),
        RiskZoneRecord(date=date(2026, 1, 2), zone_id="Bus-Zone", risk_intensity=0.74),
        RiskZoneRecord(date=date(2026, 1, 3), zone_id="Stairs-1", risk_intensity=0.7),
    ]


def test_ssi_accuracy_for_semester_index() -> None:
    service = MinistryReportService(required_benchmark_ssi=75.0)
    report = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="Al Noor School",
        period_label="Spring 2026",
        ssi_daily_scores=_sample_daily_scores(),
        heatmap_risk_records=_sample_risk_records(),
    )

    assert report["semester_ssi_index"] == 80.0


def test_standard_comparison_below_at_above() -> None:
    service = MinistryReportService(required_benchmark_ssi=75.0, at_band_tolerance=0.5)

    below = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="School A",
        period_label="S1",
        ssi_daily_scores=[SSIDailyScore(date=date(2026, 1, 1), score=70.0)],
        heatmap_risk_records=[],
    )
    at = service.generate_ministerial_summary(
        school_id="SCH-02",
        school_name="School B",
        period_label="S1",
        ssi_daily_scores=[SSIDailyScore(date=date(2026, 1, 1), score=75.2)],
        heatmap_risk_records=[],
    )
    above = service.generate_ministerial_summary(
        school_id="SCH-03",
        school_name="School C",
        period_label="S1",
        ssi_daily_scores=[SSIDailyScore(date=date(2026, 1, 1), score=82.0)],
        heatmap_risk_records=[],
    )

    assert below["benchmark"]["status"] == "Below"
    assert at["benchmark"]["status"] == "At"
    assert above["benchmark"]["status"] == "Above"


def test_scalability_transfer_model_levels_are_supported() -> None:
    service = MinistryReportService(required_benchmark_ssi=75.0)

    minimum = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="School A",
        period_label="S1",
        ssi_daily_scores=_sample_daily_scores(),
        heatmap_risk_records=_sample_risk_records(),
        scalability_level="minimum",
    )
    standard = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="School A",
        period_label="S1",
        ssi_daily_scores=_sample_daily_scores(),
        heatmap_risk_records=_sample_risk_records(),
        scalability_level="standard",
    )
    extended = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="School A",
        period_label="S1",
        ssi_daily_scores=_sample_daily_scores(),
        heatmap_risk_records=_sample_risk_records(),
        scalability_level="extended",
    )

    assert minimum["scalability_transfer_model"]["level"] == "minimum"
    assert "summary_metrics" not in minimum

    assert standard["scalability_transfer_model"]["level"] == "standard"
    assert "summary_metrics" in standard

    assert extended["scalability_transfer_model"]["level"] == "extended"
    assert "summary_metrics" in extended
    assert "extended_analytics" in extended


def test_anonymization_compliance_aggregated_only_output() -> None:
    service = MinistryReportService(required_benchmark_ssi=75.0)
    report = service.generate_ministerial_summary(
        school_id="SCH-01",
        school_name="School A",
        period_label="S1",
        ssi_daily_scores=_sample_daily_scores(),
        heatmap_risk_records=_sample_risk_records(),
    )

    compliance = report["governance_compliance"]
    assert compliance["aggregated_only"] is True
    assert compliance["contains_minor_video_frames"] is False
    assert compliance["pii_included"] is False

    report_text = str(report).lower()
    assert "frame" not in report_text or "contains_minor_video_frames': false" in report_text
