from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np


class Role(str, Enum):
    TEACHER = "Teacher"
    PRINCIPAL = "Principal"
    MINISTRY = "Ministry"


class Action(str, Enum):
    VIEW_CLASSROOM_FEED = "view_classroom_feed"
    VIEW_SCHOOL_ANALYTICS = "view_school_analytics"
    VIEW_SYSTEM_WIDE_ANALYTICS = "view_system_wide_analytics"
    MANAGE_RETENTION_POLICY = "manage_retention_policy"


@dataclass(frozen=True)
class GovernancePolicy:
    model_name: str = "Arab Data Governance Model"
    minor_age_threshold: int = 18
    default_video_ttl_hours: int = 72


POLICY = GovernancePolicy()

ROLE_PERMISSIONS: dict[Role, set[Action]] = {
    Role.TEACHER: {Action.VIEW_CLASSROOM_FEED},
    Role.PRINCIPAL: {
        Action.VIEW_CLASSROOM_FEED,
        Action.VIEW_SCHOOL_ANALYTICS,
        Action.MANAGE_RETENTION_POLICY,
    },
    Role.MINISTRY: {
        Action.VIEW_CLASSROOM_FEED,
        Action.VIEW_SCHOOL_ANALYTICS,
        Action.VIEW_SYSTEM_WIDE_ANALYTICS,
        Action.MANAGE_RETENTION_POLICY,
    },
}

SCOPE_LEVEL: dict[Role, int] = {
    Role.TEACHER: 1,
    Role.PRINCIPAL: 2,
    Role.MINISTRY: 3,
}


def _load_default_face_detector() -> cv2.CascadeClassifier:
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if detector.empty():
        raise RuntimeError("Failed to load OpenCV face detector cascade.")
    return detector


def anonymize_minor_faces(
    frame: np.ndarray,
    age_estimator: Callable[[np.ndarray], int] | None = None,
    blur_kernel: tuple[int, int] = (51, 51),
    detector: cv2.CascadeClassifier | None = None,
    minor_age_threshold: int = POLICY.minor_age_threshold,
) -> np.ndarray:
    """Automated anonymization by blurring detected minor faces.

    When an age estimator is not supplied, this uses a conservative policy and
    anonymizes all detected faces to prevent accidental exposure.
    """
    if frame is None or frame.size == 0:
        raise ValueError("Input frame must be a non-empty image array.")

    if blur_kernel[0] % 2 == 0 or blur_kernel[1] % 2 == 0:
        raise ValueError("Blur kernel dimensions must be odd numbers.")

    detector = detector or _load_default_face_detector()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    anonymized = frame.copy()
    for (x, y, w, h) in faces:
        face_region = anonymized[y : y + h, x : x + w]
        estimated_age = age_estimator(face_region) if age_estimator else 0
        if estimated_age < minor_age_threshold:
            anonymized[y : y + h, x : x + w] = cv2.GaussianBlur(face_region, blur_kernel, 0)

    return anonymized


def enforce_video_log_ttl(
    logs_path: str | Path,
    ttl_hours: int = POLICY.default_video_ttl_hours,
    now: datetime | None = None,
    allowed_suffixes: Iterable[str] = (".mp4", ".avi", ".mov", ".mkv"),
) -> list[Path]:
    """Delete expired video files according to strict TTL policy."""
    if ttl_hours <= 0:
        raise ValueError("ttl_hours must be greater than zero.")

    base_path = Path(logs_path)
    if not base_path.exists():
        return []

    current_time = now or datetime.now(timezone.utc)
    expiry_delta = timedelta(hours=ttl_hours)
    normalized_suffixes = {suffix.lower() for suffix in allowed_suffixes}

    deleted_files: list[Path] = []
    for file_path in base_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in normalized_suffixes:
            continue

        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if current_time - modified_time > expiry_delta:
            file_path.unlink(missing_ok=True)
            deleted_files.append(file_path)

    return deleted_files


def has_role_permission(role: Role, action: Action) -> bool:
    return action in ROLE_PERMISSIONS.get(role, set())


def check_educational_hierarchy_access(
    requester_role: Role,
    requester_scope_id: str,
    target_scope_id: str,
    action: Action,
) -> bool:
    """RBAC enforcement for Teacher -> Principal -> Ministry hierarchy."""
    if not has_role_permission(requester_role, action):
        return False

    if requester_role is Role.MINISTRY:
        return True

    if requester_role is Role.PRINCIPAL:
        return requester_scope_id == target_scope_id

    if requester_role is Role.TEACHER:
        return action == Action.VIEW_CLASSROOM_FEED and requester_scope_id == target_scope_id

    return False
