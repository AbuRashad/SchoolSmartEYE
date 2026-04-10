"""Unit 14: Arab Data Governance Layer — نموذج الحوكمة والخصوصية العربية."""
from __future__ import annotations

from app.core.governance_layer import (
    GovernancePolicy,
    Role,
    Action,
    POLICY,
    ROLE_PERMISSIONS,
    anonymize_minor_faces,
    enforce_video_log_ttl,
    has_role_permission,
    check_educational_hierarchy_access,
)

UNIT_14_NAME = "Arab Data Governance & Privacy Layer"

__all__ = [
    "UNIT_14_NAME",
    "GovernancePolicy",
    "Role",
    "Action",
    "POLICY",
    "ROLE_PERMISSIONS",
    "anonymize_minor_faces",
    "enforce_video_log_ttl",
    "has_role_permission",
    "check_educational_hierarchy_access",
]
