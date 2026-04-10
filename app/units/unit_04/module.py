"""Unit 04: Hazard Indicator Detection — كشف السقوط، التدافع، الشجار، البقاء غير المبرر."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import numpy as np

UNIT_04_NAME = "Hazard Indicator Detection Unit"


class HazardType(str, Enum):
    FALL = "fall"
    STAMPEDE = "stampede"
    FIGHT = "fight"
    LOITERING = "loitering"
    CROWD_SURGE = "crowd_surge"
    NONE = "none"


@dataclass(frozen=True)
class HazardEvent:
    hazard_type: HazardType
    zone_id: str
    confidence: float          # [0,1]
    detected_at: datetime
    risk_level: str            # "low" | "medium" | "high" | "critical"
    description: str


def _risk_level(confidence: float) -> str:
    if confidence >= 0.85:
        return "critical"
    if confidence >= 0.65:
        return "high"
    if confidence >= 0.40:
        return "medium"
    return "low"


class HazardDetectionUnit:
    """Detects falls, stampedes, fights, and loitering from flow/density signals."""

    # Thresholds tuned from literature (adjustable per school via config)
    FALL_SUDDEN_STOP_THRESHOLD = 0.75
    STAMPEDE_SURGE_THRESHOLD = 0.80
    FIGHT_ENTROPY_THRESHOLD = 0.72
    LOITERING_DENSITY_LOW = 0.05
    LOITERING_DURATION_FRAMES = 30

    def __init__(self) -> None:
        self._loitering_counter: dict[str, int] = {}

    def analyze_frame(
        self,
        zone_id: str,
        flow_magnitude: float,       # avg optical-flow magnitude in zone
        prev_flow_magnitude: float,  # previous frame magnitude
        crowd_density: float,        # [0,1]
        movement_entropy: float,     # [0,1] from scene understanding
        detected_at: datetime | None = None,
    ) -> HazardEvent | None:
        ts = detected_at or datetime.utcnow()

        # Fall: sudden large magnitude drop after movement
        if prev_flow_magnitude > 1.5 and flow_magnitude < 0.3:
            confidence = float(np.clip(
                (prev_flow_magnitude - flow_magnitude) / max(prev_flow_magnitude, 1e-6),
                0.0, 1.0,
            ))
            if confidence >= self.FALL_SUDDEN_STOP_THRESHOLD:
                return HazardEvent(
                    hazard_type=HazardType.FALL,
                    zone_id=zone_id,
                    confidence=confidence,
                    detected_at=ts,
                    risk_level=_risk_level(confidence),
                    description=f"Sudden movement stop detected in {zone_id}.",
                )

        # Stampede: very high density + high magnitude
        if crowd_density >= self.STAMPEDE_SURGE_THRESHOLD and flow_magnitude > 2.0:
            confidence = float(np.clip(crowd_density * (flow_magnitude / 3.0), 0.0, 1.0))
            return HazardEvent(
                hazard_type=HazardType.STAMPEDE,
                zone_id=zone_id,
                confidence=confidence,
                detected_at=ts,
                risk_level=_risk_level(confidence),
                description=f"High-density crowd surge in {zone_id}.",
            )

        # Fight: high entropy + moderate-high density
        if movement_entropy >= self.FIGHT_ENTROPY_THRESHOLD and crowd_density >= 0.35:
            confidence = float(np.clip(movement_entropy * crowd_density * 1.5, 0.0, 1.0))
            return HazardEvent(
                hazard_type=HazardType.FIGHT,
                zone_id=zone_id,
                confidence=confidence,
                detected_at=ts,
                risk_level=_risk_level(confidence),
                description=f"Chaotic movement pattern indicating possible conflict in {zone_id}.",
            )

        # Loitering: low density, low flow, persistent
        if crowd_density <= self.LOITERING_DENSITY_LOW and flow_magnitude < 0.5:
            self._loitering_counter[zone_id] = self._loitering_counter.get(zone_id, 0) + 1
            if self._loitering_counter[zone_id] >= self.LOITERING_DURATION_FRAMES:
                confidence = float(np.clip(
                    self._loitering_counter[zone_id] / (self.LOITERING_DURATION_FRAMES * 2),
                    0.0, 1.0,
                ))
                return HazardEvent(
                    hazard_type=HazardType.LOITERING,
                    zone_id=zone_id,
                    confidence=confidence,
                    detected_at=ts,
                    risk_level=_risk_level(confidence),
                    description=f"Prolonged unexplained stationary presence in {zone_id}.",
                )
        else:
            self._loitering_counter[zone_id] = 0

        return None
