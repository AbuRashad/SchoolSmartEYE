import numpy as np

from app.services.collective_behavioral_coherence import CollectiveBehavioralCoherence


def test_highly_aligned_vectors_produce_high_coherence() -> None:
    analyzer = CollectiveBehavioralCoherence(min_vectors=5)
    vectors = np.tile(np.array([[2.0, 0.0]], dtype=np.float32), (100, 1))

    coherence, entropy, divergence = analyzer.analyze_vectors(vectors)

    assert coherence > 0.95
    assert entropy < 0.2
    assert divergence < 0.05


def test_divergent_vectors_produce_low_coherence_and_high_entropy() -> None:
    analyzer = CollectiveBehavioralCoherence(min_vectors=5)
    vectors = np.array(
        [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]] * 30,
        dtype=np.float32,
    )

    coherence, entropy, divergence = analyzer.analyze_vectors(vectors)

    assert coherence < 0.2
    assert entropy >= 0.5
    assert divergence > 0.6


def test_coherence_rupture_flags_after_synchrony_collapse() -> None:
    analyzer = CollectiveBehavioralCoherence(
        min_vectors=5,
        baseline_warmup_frames=4,
        std_scale=1.5,
    )

    aligned = np.tile(np.array([[1.5, 0.0]], dtype=np.float32), (120, 1))
    for _ in range(6):
        coherence, entropy, divergence = analyzer.analyze_vectors(aligned)
        analyzer._coherence_history.append(coherence)
        analyzer._entropy_history.append(entropy)
        analyzer._divergence_history.append(divergence)

    divergent = np.array(
        [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]] * 40,
        dtype=np.float32,
    )
    coherence, entropy, divergence = analyzer.analyze_vectors(divergent)
    thresholds = analyzer._dynamic_thresholds()

    assert analyzer._is_coherence_rupture(coherence, entropy, divergence, thresholds)
