"""Per-role metric scoping for the SchoolSmartEYE specialist agents.

Each specialist receives only the aggregate metrics its role is accountable for.
The deterministic agents still run over the full validated metric set, so no
existing finding changes; scoping applies to the model payload only.

`None` means "no restriction" and is reserved for the two roles whose job is to
judge the whole evidence set rather than a slice of it.
"""
from __future__ import annotations

# Sentinel scope: the role reviews every validated metric.
FULL_SCOPE: None = None

AGENT_METRIC_SCOPE: dict[str, frozenset[str] | None] = {
    # Interprets aggregate school metrics, patterns and data gaps.
    "analytics": frozenset({"attendance_rate", "total_students", "total_units"}),
    # Reviews safety signals and crowd pressure; needs cameras to confirm coverage.
    "safety": frozenset({
        "incidents_today", "incidents_week", "avg_crowd_density",
        "attendance_rate", "active_cameras", "total_students",
    }),
    # Interprets learning and attendance indicators.
    "academic": frozenset({"attendance_rate", "total_students", "compliance_score"}),
    # Reviews operational reliability and service indicators.
    "operations": frozenset({
        "uptime_percent", "active_cameras", "alerts_resolved_today",
        "patrol_efficiency", "total_units",
    }),
    # Judges sufficiency and consistency of the whole evidence set.
    "evidence": FULL_SCOPE,
    # Reviews uncertainty, bias and privacy across all roles.
    "ethics_review": FULL_SCOPE,
}

# Number of prior agent analyses forwarded as peer context.
MAX_PEER_HANDOFF = 5


def metric_scope_for(agent_name: str) -> frozenset[str] | None:
    """Return the role's metric scope, or the full scope for an unknown role.

    An unrecognised agent name is treated as unrestricted rather than empty so a
    newly added role cannot silently starve the model of all input.
    """
    return AGENT_METRIC_SCOPE.get(agent_name, FULL_SCOPE)


def scope_metrics(
    agent_name: str,
    metrics: dict[str, int | float],
) -> dict[str, int | float]:
    """Filter validated metrics down to the role's scope.

    Ordering follows the caller's dict so evidence stays stable across roles.
    """
    scope = metric_scope_for(agent_name)
    if scope is None:
        return dict(metrics)
    return {key: value for key, value in metrics.items() if key in scope}


def scoped_metric_names(agent_name: str) -> list[str]:
    """Sorted metric names for the role, for docs and tests."""
    scope = metric_scope_for(agent_name)
    return sorted(scope) if scope is not None else []
