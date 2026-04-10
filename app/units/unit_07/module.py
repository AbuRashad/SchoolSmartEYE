"""Unit 07: Predictive Density Unit — wraps CrowdDensityForecaster as a named unit."""
from __future__ import annotations

from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityPrediction

UNIT_07_NAME = "Predictive Density Unit"

__all__ = ["UNIT_07_NAME", "CrowdDensityForecaster", "DensityPrediction"]
