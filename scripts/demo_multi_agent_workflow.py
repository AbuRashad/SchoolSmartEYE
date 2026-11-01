"""Run a privacy-safe synthetic SchoolSmartEYE multi-agent demonstration.

From the repository root:
    python scripts/demo_multi_agent_workflow.py

The scenario contains synthetic school-wide aggregate metrics only. It does not
read the database, contact students, or perform operational actions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the repository root importable when this file is executed directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.agent_orchestrator import run_orchestration  # noqa: E402


SYNTHETIC_SCENARIO = {
    "attendance_rate": 87.5,
    "total_students": 640,
    "active_cameras": 12,
    "total_units": 15,
    "incidents_today": 2,
    "incidents_week": 5,
    "avg_crowd_density": 0.81,
    "uptime_percent": 98.6,
    "alerts_resolved_today": 4,
    "patrol_efficiency": 82,
    "compliance_score": 91,
    "data_status": "demo",
    "data_notice": "Synthetic demonstration data; not a real school feed.",
}


def main() -> int:
    result = run_orchestration(
        "Review the synthetic school-wide signals, identify evidence gaps, "
        "and prepare a human-reviewed response plan.",
        SYNTHETIC_SCENARIO,
    )

    print("SchoolSmartEYE | Multi-Agent Workflow Demonstration")
    print("=" * 58)
    print(f"Request ID: {result['request_id']}")
    print(f"Data status: {result['report']['data_status']}")
    print(f"Provider: {result['provider']}")
    print(f"Specialist stages: {len(result['stages'])}")
    print(f"AI-assisted stages: {result['report']['ai_agent_count']}")
    print(f"Evidence items: {result['report']['evidence_count']}")
    print()
    for stage in result["stages"]:
        print(
            f"- {stage['name']}: {stage['analysis_status']} "
            f"({stage.get('provider', 'deterministic')})"
        )
        if stage.get("advisory_summary"):
            print(f"  Advisory: {stage['advisory_summary']}")
        elif stage.get("summary"):
            print(f"  Rule-based: {stage['summary']}")

    print()
    print("Human review required:", result["requires_human_review"])
    print("Autonomous action taken:", result["autonomous_action_taken"])
    print("Data notice:", result["report"]["data_notice"])
    print()
    print("Limitations:")
    for item in result["report"]["limitations"]:
        print(f"- {item}")

    if "--json" in sys.argv[1:]:
        print()
        print("Full structured result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    # A limited result is still a successful demonstration of safe fallback.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
