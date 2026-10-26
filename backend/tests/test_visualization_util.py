from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from utils import visualization_util


def synthetic_frames(count):
    return [np.full((48, 64, 3), index * 10, dtype=np.uint8) for index in range(count)]


def test_analysis_figure_matches_vigil_layout():
    frames = synthetic_frames(12)
    predictions = np.linspace(0.05, 0.95, 12)
    figure, artists = visualization_util.build_analysis_figure(
        frames, predictions, [1, 3, 5, 7, 9, 11]
    )
    try:
        assert figure.get_size_inches().tolist() == [12.8, 7.2]
        np.testing.assert_allclose(figure.get_facecolor()[:3], (1 / 255, 3 / 255, 1 / 255))
        assert len(artists["thumbnail_axes"]) == 6
        assert artists["graph_axis"].get_position().x0 > 0.68
        assert artists["score_line"].get_color() == "#50E326"
        assert artists["status_text"].get_text() == "MONITORING"
    finally:
        plt.close(figure)


def test_visualize_predictions_writes_landscape_gif_and_detected_frames(
    tmp_path, monkeypatch
):
    frames = synthetic_frames(12)
    predictions = np.array(
        [0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4, 0.4, 0.5, 0.5, 0.6]
    )
    monkeypatch.setattr(visualization_util, "get_video_frames", lambda _: frames)
    gif_path = tmp_path / "out.gif"

    indices = visualization_util.visualize_predictions(
        Path("video.mp4"), predictions, gif_path, tmp_path
    )

    assert indices == [1, 3, 5, 7, 9, 11]
    assert len(list(tmp_path.glob("fr*.png"))) == 6
    with Image.open(gif_path) as gif:
        assert gif.width > gif.height
        assert gif.n_frames == 2


def test_elevated_score_uses_red_status_and_frame_borders():
    frames = synthetic_frames(12)
    predictions = np.linspace(0.1, 0.9, 12)
    figure, artists = visualization_util.build_analysis_figure(
        frames, predictions, [1, 3, 5, 7, 9, 11]
    )
    try:
        visualization_util._update_analysis_figure(artists, frames, predictions, 11)
        assert artists["status_text"].get_text() == "ELEVATED"
        assert artists["status_text"].get_color() == "#FF4D4D"
        assert artists["thumbnail_axes"][-1].spines["left"].get_edgecolor()[:3] == (
            1.0,
            77 / 255,
            77 / 255,
        )
    finally:
        plt.close(figure)
