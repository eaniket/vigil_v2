import numpy as np
import pytest

from utils.array_util import extrapolate, interpolate, sliding_window


def test_sliding_window_keeps_final_partial_window():
    assert sliding_window(list(range(5)), 2, 2) == [[0, 1], [2, 3], [4]]


def test_sliding_window_rejects_invalid_sizes():
    with pytest.raises(ValueError, match="positive"):
        sliding_window([1, 2], 0, 1)


def test_interpolate_returns_normalized_fixed_size_bag():
    features = np.arange(1, 25, dtype=np.float32).reshape(6, 4)
    result = interpolate(features, 8)
    assert result.shape == (8, 4)
    np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1.0, atol=1e-6)


def test_interpolate_rejects_empty_and_zero_norm_features():
    with pytest.raises(ValueError, match="non-empty"):
        interpolate(np.empty((0, 4)), 8)
    with pytest.raises(ValueError, match="invalid norm"):
        interpolate(np.zeros((2, 4)), 8)


def test_extrapolate_matches_requested_frame_count():
    result = extrapolate(np.array([0.1, 0.5, 0.9]), 7)
    assert result.shape == (7,)
    assert result[0] == pytest.approx(0.1)
    assert result[-1] == pytest.approx(0.9)
