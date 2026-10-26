import numpy as np
import pytest

from c3d import C3D, preprocess_input
from classifier import build_classifier_model


def test_preprocess_input_shape(tmp_path):
    mean_path = tmp_path / "mean.npy"
    np.save(mean_path, np.zeros((16, 128, 171, 3), dtype=np.float32))
    video = np.zeros((16, 240, 320, 3), dtype=np.uint8)
    processed = preprocess_input(video, mean_path=mean_path)
    assert processed.shape == (1, 16, 112, 112, 3)
    assert processed.dtype == np.float32


def test_preprocess_input_rejects_short_video(tmp_path):
    with pytest.raises(ValueError, match="at least 16"):
        preprocess_input(np.zeros((15, 20, 20, 3)), mean_path=tmp_path / "mean.npy")


def test_classifier_loads_matlab_weights_and_predicts():
    model = build_classifier_model()
    predictions = model.predict(np.zeros((32, 4096), dtype=np.float32), verbose=0)
    assert predictions.shape == (32, 1)
    assert np.all(np.isfinite(predictions))


def test_c3d_legacy_weights_load_into_modern_model():
    model = C3D()
    assert model.input_shape == (None, 16, 112, 112, 3)
    assert model.output_shape == (None, 487)
    assert model.count_params() == 79_991_015
