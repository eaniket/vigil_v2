from pathlib import Path

import pytest

from inference_service import InferenceBusyError, InferenceService


def test_models_are_loaded_once_and_upload_is_cleaned(tmp_path):
    calls = {"loads": 0, "runs": 0}

    def loader():
        calls["loads"] += 1
        return "feature-model", "classifier-model"

    def runner(**kwargs):
        calls["runs"] += 1
        assert kwargs["feature_extractor"] == "feature-model"
        assert kwargs["classifier_model"] == "classifier-model"
        return {"frame_count": 16}

    service = InferenceService(model_loader=loader, runner=runner)
    for index in range(2):
        cleanup = tmp_path / f"upload-{index}"
        cleanup.mkdir()
        service.analyze(tmp_path / "video.mp4", tmp_path / "output", cleanup)
        assert not cleanup.exists()
    assert calls == {"loads": 1, "runs": 2}
    assert service.models_loaded


def test_busy_service_rejects_and_cleans_upload(tmp_path):
    service = InferenceService(model_loader=lambda: (None, None), runner=lambda **_: None)
    cleanup = tmp_path / "upload"
    cleanup.mkdir()
    service._lock.acquire()
    try:
        with pytest.raises(InferenceBusyError, match="currently"):
            service.analyze(Path("video.mp4"), tmp_path / "output", cleanup)
    finally:
        service._lock.release()
    assert not cleanup.exists()
