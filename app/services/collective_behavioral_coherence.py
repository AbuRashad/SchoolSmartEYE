from __future__ import annotations

from collections import deque

import cv2
import numpy as np


class CollectiveBehavioralCoherence:
    """Collective movement coherence analysis inspired by complex systems theory.

    The analyzer extracts group velocity vectors using optical flow, computes
    polarization/coherence and entropy, and flags coherence rupture when
    synchrony collapses through entropy spikes or vector divergence.
    """

    def __init__(
        self,
        method: str = "farneback",
        movement_threshold: float = 0.5,
        history_window: int = 60,
        baseline_warmup_frames: int = 8,
        std_scale: float = 2.0,
        min_vectors: int = 20,
        angle_bins: int = 16,
    ) -> None:
        method_normalized = method.lower().strip()
        if method_normalized not in {"farneback", "lucas_kanade"}:
            raise ValueError("method must be 'farneback' or 'lucas_kanade'")
        if movement_threshold <= 0:
            raise ValueError("movement_threshold must be > 0")
        if history_window < 10:
            raise ValueError("history_window must be >= 10")
        if baseline_warmup_frames < 3:
            raise ValueError("baseline_warmup_frames must be >= 3")
        if std_scale <= 0:
            raise ValueError("std_scale must be > 0")
        if min_vectors <= 0:
            raise ValueError("min_vectors must be > 0")
        if angle_bins < 8:
            raise ValueError("angle_bins must be >= 8")

        self.method = method_normalized
        self.movement_threshold = movement_threshold
        self.history_window = history_window
        self.baseline_warmup_frames = baseline_warmup_frames
        self.std_scale = std_scale
        self.min_vectors = min_vectors
        self.angle_bins = angle_bins

        self._prev_gray: np.ndarray | None = None
        self._frame_shape: tuple[int, int] | None = None

        self._coherence_history: deque[float] = deque(maxlen=history_window)
        self._entropy_history: deque[float] = deque(maxlen=history_window)
        self._divergence_history: deque[float] = deque(maxlen=history_window)

    def process_frame(self, frame_bgr: np.ndarray) -> dict[str, object]:
        """Process a frame and produce collective coherence metrics and rupture flag."""
        if frame_bgr is None or frame_bgr.size == 0:
            raise ValueError("frame_bgr must be a non-empty BGR image")

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        if self._frame_shape is None:
            self._frame_shape = (h, w)
        elif self._frame_shape != (h, w):
            raise ValueError("All frames must have the same shape")

        if self._prev_gray is None:
            self._prev_gray = gray
            return self._empty_result()

        vectors = self._extract_velocity_vectors(self._prev_gray, gray)
        self._prev_gray = gray

        coherence, entropy, divergence = self.analyze_vectors(vectors)
        self._coherence_history.append(coherence)
        self._entropy_history.append(entropy)
        self._divergence_history.append(divergence)

        thresholds = self._dynamic_thresholds()
        rupture = self._is_coherence_rupture(coherence, entropy, divergence, thresholds)

        reasons: list[str] = []
        if coherence < thresholds["coherence_floor"]:
            reasons.append("coherence_collapse")
        if entropy > thresholds["entropy_ceiling"]:
            reasons.append("entropy_spike")
        if divergence > thresholds["divergence_ceiling"]:
            reasons.append("vector_divergence")

        return {
            "method": self.method,
            "polarization": coherence,
            "coherence": coherence,
            "entropy": entropy,
            "divergence": divergence,
            "coherence_rupture": rupture,
            "reasons": reasons,
            "thresholds": thresholds,
            "vector_count": int(vectors.shape[0]),
        }

    def analyze_vectors(self, vectors: np.ndarray) -> tuple[float, float, float]:
        """Compute coherence, entropy, and divergence from velocity vectors."""
        if vectors.size == 0:
            return 0.0, 1.0, 1.0

        magnitudes = np.linalg.norm(vectors, axis=1)
        moving = vectors[magnitudes > self.movement_threshold]
        if moving.shape[0] < self.min_vectors:
            return 0.0, 1.0, 1.0

        moving_norm = moving / np.maximum(np.linalg.norm(moving, axis=1, keepdims=True), 1e-8)
        mean_vector = np.mean(moving_norm, axis=0)

        polarization = float(np.linalg.norm(mean_vector))
        coherence = float(np.clip(polarization, 0.0, 1.0))

        angles = np.arctan2(moving_norm[:, 1], moving_norm[:, 0])
        hist, _ = np.histogram(angles, bins=self.angle_bins, range=(-np.pi, np.pi), density=False)
        probs = hist.astype(np.float64)
        probs = probs / np.maximum(np.sum(probs), 1.0)
        non_zero = probs[probs > 0]
        entropy = float(-np.sum(non_zero * np.log(non_zero)) / np.log(self.angle_bins))
        entropy = float(np.clip(entropy, 0.0, 1.0))

        cosine_to_group = np.dot(moving_norm, mean_vector / np.maximum(np.linalg.norm(mean_vector), 1e-8))
        divergence = float(np.clip(1.0 - np.mean(np.clip(cosine_to_group, -1.0, 1.0)), 0.0, 1.0))

        return coherence, entropy, divergence

    def _extract_velocity_vectors(self, prev_gray: np.ndarray, gray: np.ndarray) -> np.ndarray:
        if self.method == "farneback":
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray,
                gray,
                None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0,
            )
            return flow.reshape(-1, 2)

        feature_points = cv2.goodFeaturesToTrack(
            prev_gray,
            maxCorners=800,
            qualityLevel=0.01,
            minDistance=5,
            blockSize=7,
        )

        if feature_points is None or len(feature_points) == 0:
            return np.zeros((0, 2), dtype=np.float32)

        next_points, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray,
            gray,
            feature_points,
            None,
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
        )

        if next_points is None or status is None:
            return np.zeros((0, 2), dtype=np.float32)

        good_old = feature_points[status.flatten() == 1]
        good_new = next_points[status.flatten() == 1]
        if good_old.shape[0] == 0:
            return np.zeros((0, 2), dtype=np.float32)

        vectors = good_new - good_old
        return vectors.reshape(-1, 2)

    def _dynamic_thresholds(self) -> dict[str, float]:
        if len(self._coherence_history) < self.baseline_warmup_frames:
            return {
                "coherence_floor": 0.35,
                "entropy_ceiling": 0.75,
                "divergence_ceiling": 0.65,
            }

        coh = np.asarray(self._coherence_history, dtype=np.float64)
        ent = np.asarray(self._entropy_history, dtype=np.float64)
        div = np.asarray(self._divergence_history, dtype=np.float64)

        coh_floor = float(np.clip(np.mean(coh) - self.std_scale * np.std(coh), 0.0, 1.0))
        ent_ceil = float(np.clip(np.mean(ent) + self.std_scale * np.std(ent), 0.0, 1.0))
        div_ceil = float(np.clip(np.mean(div) + self.std_scale * np.std(div), 0.0, 1.0))

        return {
            "coherence_floor": coh_floor,
            "entropy_ceiling": ent_ceil,
            "divergence_ceiling": div_ceil,
        }

    def _is_coherence_rupture(
        self,
        coherence: float,
        entropy: float,
        divergence: float,
        thresholds: dict[str, float],
    ) -> bool:
        return (
            coherence < thresholds["coherence_floor"]
            or entropy > thresholds["entropy_ceiling"]
            or divergence > thresholds["divergence_ceiling"]
        )

    def _empty_result(self) -> dict[str, object]:
        return {
            "method": self.method,
            "polarization": 0.0,
            "coherence": 0.0,
            "entropy": 1.0,
            "divergence": 1.0,
            "coherence_rupture": False,
            "reasons": [],
            "thresholds": self._dynamic_thresholds(),
            "vector_count": 0,
        }
