"""First-party school-domain intelligence; no network or third-party model calls."""
from typing import Any

ROLES = ("analytics", "safety", "academic", "operations", "evidence", "ethics_review")


def analyze_specialist(agent: str, metrics: dict[str, int | float], peers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if agent not in ROLES:
        return {}
    observations: list[str] = []
    questions: list[str] = []
    risks: list[str] = []
    attendance = metrics.get("attendance_rate")
    incidents = metrics.get("incidents_today")
    crowd = metrics.get("avg_crowd_density")
    uptime = metrics.get("uptime_percent")
    if agent == "analytics":
        observations.append(f"Evaluated {len(metrics)} approved aggregate indicators.")
        if attendance is not None and incidents is not None and attendance < 90 and incidents > 0:
            observations.append("Low attendance and a non-zero incident count coexist; this does not establish causation.")
            questions.append("Do both indicators cover the same period and population?")
        questions.append("Are all indicators current and traceable to approved sources?")
        summary = "Native analytics checked cross-indicator consistency and data quality."
    elif agent == "safety":
        if incidents is not None and incidents > 0:
            observations.append(f"Aggregate incident indicator: {incidents}.")
            questions.append("Have authorized staff verified and classified the source reports?")
        if crowd is not None and crowd >= 0.75:
            risks.append("Elevated aggregate crowd-density signal requires on-site verification.")
        summary = "Native safety reasoning reviewed incident and density signals."
    elif agent == "academic":
        if attendance is not None:
            observations.append(f"School-wide attendance: {attendance:.1f}%.")
            if attendance < 90:
                risks.append("Attendance is below the review threshold; aggregate data cannot explain individual barriers.")
                questions.append("Which school-level barriers should educators investigate?")
        summary = "Native academic reasoning prepared supportive school-level review questions."
    elif agent == "operations":
        if uptime is not None:
            observations.append(f"Reported service uptime: {uptime:.1f}%.")
            if uptime < 99:
                risks.append("Service uptime is below the 99% operational review threshold.")
        if metrics.get("active_cameras") == 0:
            risks.append("No active cameras are reported; verify whether expected.")
        summary = "Native operations reasoning checked service and coverage indicators."
    elif agent == "evidence":
        observations.append(f"Evidence contains {len(metrics)} approved aggregate indicators.")
        if len(metrics) < 3:
            questions.append("Which additional approved aggregate sources are needed?")
        if not metrics:
            risks.append("No validated aggregate evidence is available.")
        summary = "Native evidence reasoning checked sufficiency and traceability."
    else:
        peer_count = len(peers or [])
        observations.append(f"Cross-reviewed {peer_count} specialist analyses.")
        if peer_count < 5:
            risks.append("Peer review is incomplete.")
        questions.append("Has a school leader reviewed uncertainty, privacy and proportionality?")
        summary = "Native ethics reasoning reviewed peer outputs and governance risks."
    return {
        "summary": summary[:500],
        "observations": [x[:240] for x in observations[:5]],
        "follow_up_questions": [x[:240] for x in questions[:5]],
        "risks": [x[:240] for x in risks[:5]],
    }
