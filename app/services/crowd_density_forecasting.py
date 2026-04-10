from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np


@dataclass(frozen=True)
class ForecastResult:
    predicted_density_map: np.ndarray
    risk_heatmap: np.ndarray


@dataclass(frozen=True)
class DensityObservation:
    location: str
    timestamp: datetime
    density: float


@dataclass(frozen=True)
class DensityPrediction:
    location: str
    forecast_time: datetime
    predicted_density: float
    safety_threshold: float
    risk_level: str
    warning: bool
    model_type: str


class CrowdDensityForecaster:
    """Predictive density model using a simulated LSTM/GPR-style forecaster.

    The predictor learns spatio-temporal density patterns from historical
    observations keyed by location, time of day, and day of week, then forecasts
    crowd density 15-30 minutes ahead and returns a zone risk level.
    """

    def __init__(
        self,
        safety_threshold: float = 0.75,
        default_horizon_minutes: int = 15,
        model_type: str = "simulated_lstm",
        time_sigma_minutes: float = 45.0,
    ) -> None:
        if not (0.0 <= safety_threshold <= 1.0):
            raise ValueError("safety_threshold must be in [0.0, 1.0]")
        if default_horizon_minutes <= 0:
            raise ValueError("default_horizon_minutes must be greater than zero")
        if model_type not in {"simulated_lstm", "simulated_gpr"}:
            raise ValueError("model_type must be 'simulated_lstm' or 'simulated_gpr'")
        if time_sigma_minutes <= 0:
            raise ValueError("time_sigma_minutes must be greater than zero")

        self.safety_threshold = safety_threshold
        self.default_horizon_minutes = default_horizon_minutes
        self.model_type = model_type
        self.time_sigma_minutes = time_sigma_minutes
        self._observations: list[DensityObservation] = []

    def fit(self, historical_data: list[DensityObservation]) -> None:
        if not historical_data:
            raise ValueError("historical_data must not be empty")

        normalized: list[DensityObservation] = []
        for item in historical_data:
            density = float(np.clip(item.density, 0.0, 1.0))
            normalized.append(
                DensityObservation(
                    location=item.location,
                    timestamp=item.timestamp,
                    density=density,
                )
            )

        self._observations = sorted(normalized, key=lambda obs: obs.timestamp)

    def predict(self, location: str, current_time: datetime, horizon_minutes: int | None = None) -> DensityPrediction:
        if not self._observations:
            raise RuntimeError("No historical data available. Call fit() before predict().")

        horizon = horizon_minutes or self.default_horizon_minutes
        if horizon <= 0:
            raise ValueError("horizon_minutes must be greater than zero")

        forecast_time = current_time + timedelta(minutes=horizon)
        location_observations = [obs for obs in self._observations if obs.location == location]
        if not location_observations:
            raise ValueError(f"No historical density data found for location '{location}'")

        predicted_density = self._forecast_density(location_observations, forecast_time)
        risk_level = self._risk_level(predicted_density)

        return DensityPrediction(
            location=location,
            forecast_time=forecast_time,
            predicted_density=predicted_density,
            safety_threshold=self.safety_threshold,
            risk_level=risk_level,
            warning=predicted_density >= self.safety_threshold,
            model_type=self.model_type,
        )

    def _forecast_density(self, observations: list[DensityObservation], forecast_time: datetime) -> float:
        forecast_minutes = forecast_time.hour * 60 + forecast_time.minute
        weighted_sum = 0.0
        weight_total = 0.0

        for obs in observations:
            obs_minutes = obs.timestamp.hour * 60 + obs.timestamp.minute
            clock_delta = abs(obs_minutes - forecast_minutes)
            circular_delta = min(clock_delta, 1440 - clock_delta)
            time_weight = float(np.exp(-0.5 * (circular_delta / self.time_sigma_minutes) ** 2))

            weekday_weight = 1.25 if obs.timestamp.weekday() == forecast_time.weekday() else 0.8
            recency_days = abs((forecast_time.date() - obs.timestamp.date()).days)
            recency_weight = 1.0 / (1.0 + (recency_days / 7.0))

            weight = time_weight * weekday_weight * recency_weight
            weighted_sum += weight * obs.density
            weight_total += weight

        temporal_profile = weighted_sum / max(weight_total, 1e-8)

        recent = observations[-min(4, len(observations)) :]
        recent_mean = float(np.mean([obs.density for obs in recent]))

        predicted = 0.8 * temporal_profile + 0.2 * recent_mean
        return float(np.clip(predicted, 0.0, 1.0))

    def _risk_level(self, predicted_density: float) -> str:
        if predicted_density >= self.safety_threshold:
            return "high"
        if predicted_density >= self.safety_threshold * 0.75:
            return "medium"
        return "low"


class CrowdDensityLSTMForecaster:
    """LSTM forecaster for short-horizon school crowd density prediction.

    The model consumes historical spatio-temporal sequences and predicts the
    density map for the next 15 minutes (or configurable horizon).
    """

    def __init__(
        self,
        grid_rows: int,
        grid_cols: int,
        lookback_steps: int = 12,
        sample_interval_minutes: int = 5,
        forecast_horizon_minutes: int = 15,
        lstm_units: int = 64,
        dropout: float = 0.2,
    ) -> None:
        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError("grid_rows and grid_cols must be greater than zero")
        if lookback_steps < 2:
            raise ValueError("lookback_steps must be at least 2")
        if sample_interval_minutes <= 0:
            raise ValueError("sample_interval_minutes must be greater than zero")
        if forecast_horizon_minutes <= 0:
            raise ValueError("forecast_horizon_minutes must be greater than zero")
        if lstm_units <= 0:
            raise ValueError("lstm_units must be greater than zero")
        if not (0.0 <= dropout < 1.0):
            raise ValueError("dropout must be in [0.0, 1.0)")

        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.lookback_steps = lookback_steps
        self.sample_interval_minutes = sample_interval_minutes
        self.forecast_horizon_minutes = forecast_horizon_minutes
        self.lstm_units = lstm_units
        self.dropout = dropout

        self.horizon_steps = max(1, forecast_horizon_minutes // sample_interval_minutes)
        self.feature_size = grid_rows * grid_cols + 4
        self.output_size = grid_rows * grid_cols

        self._model = None

    def prepare_training_data(
        self,
        density_maps: np.ndarray,
        timestamps: list[datetime],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build LSTM tensors from historical maps + temporal context.

        Input density_maps shape: (T, grid_rows, grid_cols)
        Output X shape: (N, lookback_steps, grid_rows*grid_cols + 4)
        Output y shape: (N, grid_rows*grid_cols)
        """
        maps = np.asarray(density_maps, dtype=np.float32)
        if maps.ndim != 3:
            raise ValueError("density_maps must have shape (T, rows, cols)")
        if maps.shape[1:] != (self.grid_rows, self.grid_cols):
            raise ValueError("density_maps shape does not match configured grid")
        if maps.shape[0] != len(timestamps):
            raise ValueError("density_maps and timestamps length must match")

        min_required = self.lookback_steps + self.horizon_steps
        if maps.shape[0] < min_required:
            raise ValueError("Not enough timesteps to create training samples")

        feature_timesteps = [
            self._build_feature_vector(maps[i], timestamps[i]) for i in range(maps.shape[0])
        ]
        features = np.stack(feature_timesteps, axis=0)

        x_batches: list[np.ndarray] = []
        y_batches: list[np.ndarray] = []

        last_start = maps.shape[0] - self.lookback_steps - self.horizon_steps + 1
        for start_idx in range(last_start):
            end_idx = start_idx + self.lookback_steps
            target_idx = end_idx + self.horizon_steps - 1

            x_batches.append(features[start_idx:end_idx])
            y_batches.append(maps[target_idx].reshape(-1))

        x = np.stack(x_batches, axis=0)
        y = np.stack(y_batches, axis=0)
        return x.astype(np.float32), y.astype(np.float32)

    def build_model(self) -> object:
        """Build and compile the LSTM architecture lazily."""
        tf, keras = self._import_tensorflow_keras()

        model = keras.Sequential(
            [
                keras.layers.Input(shape=(self.lookback_steps, self.feature_size)),
                keras.layers.LSTM(self.lstm_units, return_sequences=True),
                keras.layers.Dropout(self.dropout),
                keras.layers.LSTM(max(16, self.lstm_units // 2)),
                keras.layers.Dense(self.output_size, activation="relu"),
            ]
        )
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse", metrics=["mae"])
        self._model = model
        return model

    def fit(
        self,
        density_maps: np.ndarray,
        timestamps: list[datetime],
        epochs: int = 15,
        batch_size: int = 16,
        validation_split: float = 0.2,
        verbose: int = 0,
    ) -> object:
        """Train the LSTM model on historical data."""
        if epochs <= 0:
            raise ValueError("epochs must be greater than zero")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        if not (0.0 <= validation_split < 1.0):
            raise ValueError("validation_split must be in [0.0, 1.0)")

        x_train, y_train = self.prepare_training_data(density_maps, timestamps)
        model = self._model or self.build_model()
        history = model.fit(
            x_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=verbose,
        )
        return history

    def predict_next_density_map(
        self,
        recent_density_maps: np.ndarray,
        recent_timestamps: list[datetime],
    ) -> np.ndarray:
        """Predict the density map at the configured future horizon."""
        if self._model is None:
            raise RuntimeError("Model is not trained. Call fit() or build/load a model first.")

        maps = np.asarray(recent_density_maps, dtype=np.float32)
        if maps.shape != (self.lookback_steps, self.grid_rows, self.grid_cols):
            raise ValueError("recent_density_maps must match lookback and grid dimensions")
        if len(recent_timestamps) != self.lookback_steps:
            raise ValueError("recent_timestamps length must equal lookback_steps")

        feature_sequence = np.stack(
            [self._build_feature_vector(maps[i], recent_timestamps[i]) for i in range(self.lookback_steps)],
            axis=0,
        )
        x_input = np.expand_dims(feature_sequence, axis=0).astype(np.float32)

        prediction = self._model.predict(x_input, verbose=0)
        density_map = prediction.reshape(self.grid_rows, self.grid_cols)
        return np.clip(density_map, 0.0, None).astype(np.float32)

    def predict_with_risk_heatmap(
        self,
        recent_density_maps: np.ndarray,
        recent_timestamps: list[datetime],
    ) -> ForecastResult:
        predicted = self.predict_next_density_map(recent_density_maps, recent_timestamps)
        baseline = np.mean(np.asarray(recent_density_maps, dtype=np.float32), axis=0)
        risk = self.compute_risk_heatmap(predicted, baseline)
        return ForecastResult(predicted_density_map=predicted, risk_heatmap=risk)

    @staticmethod
    def compute_risk_heatmap(predicted_map: np.ndarray, baseline_map: np.ndarray) -> np.ndarray:
        """Create a normalized risk heatmap from predicted vs baseline density."""
        predicted = np.asarray(predicted_map, dtype=np.float32)
        baseline = np.asarray(baseline_map, dtype=np.float32)

        if predicted.shape != baseline.shape:
            raise ValueError("predicted_map and baseline_map must have the same shape")

        diff = np.maximum(predicted - baseline, 0.0)
        scale = float(np.std(diff) + 1e-6)
        risk = 1.0 / (1.0 + np.exp(-(diff / scale)))
        return np.clip(risk, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def plot_risk_heatmap_matplotlib(risk_map: np.ndarray, title: str = "Spatio-Temporal Risk Heatmap") -> object:
        """Render risk heatmap with Matplotlib.

        Returns (figure, axis).
        """
        try:
            import matplotlib.pyplot as plt
        except ModuleNotFoundError as exc:
            raise RuntimeError("Matplotlib is required for heatmap plotting.") from exc

        risk = np.asarray(risk_map, dtype=np.float32)
        fig, ax = plt.subplots(figsize=(7, 5))
        image = ax.imshow(risk, cmap="YlOrRd", interpolation="nearest", vmin=0.0, vmax=1.0)
        ax.set_title(title)
        ax.set_xlabel("Zone X")
        ax.set_ylabel("Zone Y")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Risk")
        return fig, ax

    @staticmethod
    def plot_risk_heatmap_plotly(risk_map: np.ndarray, title: str = "Spatio-Temporal Risk Heatmap") -> object:
        """Render risk heatmap with Plotly for interactive dashboards."""
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError as exc:
            raise RuntimeError("Plotly is required for interactive heatmap plotting.") from exc

        risk = np.asarray(risk_map, dtype=np.float32)
        figure = go.Figure(
            data=go.Heatmap(
                z=risk,
                colorscale="YlOrRd",
                zmin=0.0,
                zmax=1.0,
                colorbar={"title": "Risk"},
            )
        )
        figure.update_layout(title=title, xaxis_title="Zone X", yaxis_title="Zone Y")
        return figure

    def _build_feature_vector(self, density_map: np.ndarray, timestamp: datetime) -> np.ndarray:
        flat_density = density_map.reshape(-1).astype(np.float32)
        temporal = self._encode_time_features(timestamp)
        return np.concatenate([flat_density, temporal], axis=0)

    @staticmethod
    def _encode_time_features(timestamp: datetime) -> np.ndarray:
        minutes = timestamp.hour * 60 + timestamp.minute
        tod_angle = 2.0 * np.pi * (minutes / 1440.0)
        dow_angle = 2.0 * np.pi * (timestamp.weekday() / 7.0)
        return np.array(
            [
                np.sin(tod_angle),
                np.cos(tod_angle),
                np.sin(dow_angle),
                np.cos(dow_angle),
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _import_tensorflow_keras() -> tuple[object, object]:
        try:
            import tensorflow as tf
            from tensorflow import keras
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "TensorFlow is required for LSTM training. Install it with: pip install tensorflow"
            ) from exc
        return tf, keras
