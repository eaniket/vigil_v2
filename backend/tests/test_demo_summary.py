import json

import numpy as np

from demo import build_summary, write_summary


def test_build_summary_uses_verified_values_and_surfaced_frames():
    predictions = np.array([0.1, 0.2, 0.9], dtype=np.float32)
    summary = build_summary(90, 5, 30.0, predictions, [12, 18, 24, 30, 36])
    assert summary["frame_count"] == 90
    assert summary["duration_seconds"] == 3.0
    assert summary["complete_clips"] == 5
    assert summary["surfaced_frame_indices"] == [12, 18, 24, 30, 36]
    assert summary["surfaced_frame_files"] == [
        "fr0.png", "fr1.png", "fr2.png", "fr3.png", "fr4.png"
    ]


def test_write_summary_replaces_temporary_file(tmp_path):
    summary = {"frame_count": 16, "analysis_file": "out.gif"}
    path = write_summary(tmp_path, summary)
    assert json.loads(path.read_text()) == summary
    assert not (tmp_path / "summary.json.tmp").exists()
