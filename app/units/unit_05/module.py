"""Unit 05: Spatial Behavioral Memory — wraps SpatialBehavioralMemory service as a named unit."""
from __future__ import annotations

from app.services.spatial_behavioral_memory import SpatialBehavioralMemory, GridCellStats

UNIT_05_NAME = "Spatial Behavioral Memory Unit"

__all__ = ["UNIT_05_NAME", "SpatialBehavioralMemory", "GridCellStats"]
