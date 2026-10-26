from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Polygon

from utils.video_util import get_video_frames


COLORS = {
    "canvas": "#010301",
    "surface": "#020702",
    "surface_raised": "#071007",
    "line": "#364A32",
    "line_soft": "#172416",
    "text": "#DFFCE8",
    "muted": "#A4C1AA",
    "quiet": "#778676",
    "green": "#25B103",
    "green_bright": "#50E326",
    "danger": "#FF4D4D",
    "warning": "#FF806D",
}
MAX_THUMBNAILS = 6
DISPLAY_THRESHOLD = 0.75


def visualize_clip(clip, convert_bgr=False, save_gif=False, file_path=None):
    figure, axis = plt.subplots()
    image = axis.imshow(clip[0])

    def update(index):
        frame = clip[index]
        if convert_bgr:
            frame = frame[:, :, ::-1]
        image.set_data(frame)
        return (image,)

    animation = FuncAnimation(figure, update, frames=len(clip), interval=100)
    try:
        if save_gif:
            animation.save(file_path, writer=PillowWriter(fps=10), dpi=80)
    finally:
        plt.close(figure)


def _style_panel(axis):
    axis.set_facecolor(COLORS["surface"])
    for spine in axis.spines.values():
        spine.set_color(COLORS["line"])
        spine.set_linewidth(0.8)


def _thumbnail_indices(anomaly_indices):
    if len(anomaly_indices) < 5:
        return []
    if len(anomaly_indices) <= MAX_THUMBNAILS:
        return list(anomaly_indices)
    positions = np.linspace(0, len(anomaly_indices) - 1, MAX_THUMBNAILS).astype(int)
    return [anomaly_indices[index] for index in positions]


def build_analysis_figure(frames, predictions, anomaly_indices):
    if not frames or len(predictions) == 0:
        raise ValueError("Analysis visualization requires frames and predictions")

    figure = plt.figure(figsize=(12.8, 7.2), facecolor=COLORS["canvas"])
    figure.text(
        0.03,
        0.955,
        "VIGIL",
        color=COLORS["text"],
        fontsize=17,
        fontweight="bold",
        va="center",
    )
    figure.text(
        0.965,
        0.955,
        "●  LIVE ANALYSIS",
        color=COLORS["green_bright"],
        fontsize=8,
        fontweight="bold",
        ha="right",
        va="center",
    )
    divider = plt.Line2D(
        [0.025, 0.975],
        [0.91, 0.91],
        transform=figure.transFigure,
        color=COLORS["line"],
        linewidth=0.7,
    )
    figure.add_artist(divider)

    video_axis = figure.add_axes((0.035, 0.245, 0.62, 0.62))
    _style_panel(video_axis)
    video_axis.set_xticks([])
    video_axis.set_yticks([])
    video_axis.set_title(
        "MONITORED FEED  /  CAM 01",
        color=COLORS["quiet"],
        fontsize=8,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    frame_image = video_axis.imshow(frames[0])
    progress_text = video_axis.text(
        0.02,
        0.035,
        f"FRAME 0001 / {len(frames):04d}",
        transform=video_axis.transAxes,
        color=COLORS["text"],
        fontsize=7,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.65,rounding_size=1.2",
            "facecolor": COLORS["canvas"],
            "edgecolor": COLORS["line"],
            "linewidth": 0.7,
        },
    )
    video_axis.text(
        0.98,
        1.04,
        "●  PROCESSING",
        transform=video_axis.transAxes,
        color=COLORS["green_bright"],
        fontsize=7,
        fontweight="bold",
        ha="right",
    )

    figure.text(
        0.04,
        0.205,
        "DETECTED MOMENTS",
        color=COLORS["quiet"],
        fontsize=7,
        fontweight="bold",
    )
    shown_indices = _thumbnail_indices(anomaly_indices)
    thumbnail_axes = []
    if shown_indices:
        gap = 0.009
        width = (0.615 - gap * (len(shown_indices) - 1)) / len(shown_indices)
        for position, frame_index in enumerate(shown_indices):
            axis = figure.add_axes((0.04 + position * (width + gap), 0.055, width, 0.13))
            _style_panel(axis)
            axis.imshow(frames[frame_index])
            axis.set_xticks([])
            axis.set_yticks([])
            axis.text(
                0.06,
                0.08,
                f"{frame_index:04d}",
                transform=axis.transAxes,
                color=COLORS["text"],
                fontsize=6,
                fontweight="bold",
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": COLORS["canvas"],
                    "edgecolor": "none",
                },
            )
            thumbnail_axes.append(axis)
    else:
        figure.text(
            0.04,
            0.12,
            "No detected moments",
            color=COLORS["muted"],
            fontsize=9,
        )

    panel_axis = figure.add_axes((0.68, 0.055, 0.295, 0.81))
    _style_panel(panel_axis)
    panel_axis.set_xticks([])
    panel_axis.set_yticks([])
    panel_axis.text(
        0.07,
        0.95,
        "ANOMALY SIGNAL",
        transform=panel_axis.transAxes,
        color=COLORS["quiet"],
        fontsize=8,
        fontweight="bold",
        va="top",
    )
    score_text = panel_axis.text(
        0.07,
        0.88,
        f"{float(predictions[0]):.3f}",
        transform=panel_axis.transAxes,
        color=COLORS["text"],
        fontsize=31,
        va="top",
    )
    status_text = panel_axis.text(
        0.93,
        0.87,
        "MONITORING",
        transform=panel_axis.transAxes,
        color=COLORS["green_bright"],
        fontsize=7,
        fontweight="bold",
        ha="right",
        va="top",
        bbox={
            "boxstyle": "round,pad=0.65,rounding_size=1.4",
            "facecolor": COLORS["surface_raised"],
            "edgecolor": COLORS["green"],
            "linewidth": 0.7,
        },
    )
    panel_axis.text(
        0.07,
        0.79,
        "LIVE CONFIDENCE",
        transform=panel_axis.transAxes,
        color=COLORS["quiet"],
        fontsize=7,
        fontweight="bold",
    )

    graph_axis = panel_axis.inset_axes((0.07, 0.28, 0.86, 0.43))
    graph_axis.set_facecolor(COLORS["surface"])
    graph_axis.set_xlim(0, max(len(frames) - 1, 1))
    graph_axis.set_ylim(0, 1.02)
    graph_axis.set_xticks(np.linspace(0, max(len(frames) - 1, 1), 5))
    graph_axis.set_yticks(np.linspace(0, 1, 6))
    graph_axis.set_xticklabels([])
    graph_axis.set_yticklabels([])
    graph_axis.tick_params(length=0)
    graph_axis.grid(color=COLORS["line_soft"], linewidth=0.6)
    for spine in graph_axis.spines.values():
        spine.set_color(COLORS["line"])
        spine.set_linewidth(0.6)
    graph_axis.axhline(DISPLAY_THRESHOLD, color=COLORS["warning"], linewidth=0.7, alpha=0.8)
    graph_axis.text(
        0,
        DISPLAY_THRESHOLD + 0.035,
        "REVIEW THRESHOLD",
        color=COLORS["warning"],
        fontsize=6,
        fontweight="bold",
    )
    x_values = np.arange(len(predictions))
    graph_axis.plot(x_values, predictions, color=COLORS["line"], linewidth=1.0)
    (score_line,) = graph_axis.plot([], [], color=COLORS["green_bright"], linewidth=2.0)
    (score_marker,) = graph_axis.plot(
        [],
        [],
        marker="o",
        markersize=7,
        markerfacecolor=COLORS["canvas"],
        markeredgecolor=COLORS["green_bright"],
        markeredgewidth=1.8,
    )
    signal_fill = Polygon(
        [[0, 0], [0, float(predictions[0])], [0, 0]],
        closed=True,
        facecolor=COLORS["green"],
        edgecolor="none",
        alpha=0.16,
    )
    graph_axis.add_patch(signal_fill)

    panel_axis.text(
        0.07,
        0.19,
        "MODEL",
        transform=panel_axis.transAxes,
        color=COLORS["quiet"],
        fontsize=6,
        fontweight="bold",
    )
    panel_axis.text(
        0.07,
        0.15,
        "C3D + FC CLASSIFIER",
        transform=panel_axis.transAxes,
        color=COLORS["text"],
        fontsize=8,
        fontweight="bold",
    )
    panel_axis.text(
        0.07,
        0.08,
        "TIMELINE",
        transform=panel_axis.transAxes,
        color=COLORS["quiet"],
        fontsize=6,
        fontweight="bold",
    )
    timeline_background = plt.Line2D(
        [0.07, 0.93],
        [0.045, 0.045],
        transform=panel_axis.transAxes,
        color=COLORS["line_soft"],
        linewidth=4,
        solid_capstyle="round",
    )
    timeline_progress = plt.Line2D(
        [0.07, 0.07],
        [0.045, 0.045],
        transform=panel_axis.transAxes,
        color=COLORS["green_bright"],
        linewidth=4,
        solid_capstyle="round",
    )
    panel_axis.add_line(timeline_background)
    panel_axis.add_line(timeline_progress)

    return figure, {
        "frame_image": frame_image,
        "graph_axis": graph_axis,
        "progress_text": progress_text,
        "score_line": score_line,
        "score_marker": score_marker,
        "score_text": score_text,
        "signal_fill": signal_fill,
        "shown_indices": shown_indices,
        "status_text": status_text,
        "thumbnail_axes": thumbnail_axes,
        "timeline_progress": timeline_progress,
        "video_axis": video_axis,
    }


def _update_analysis_figure(artists, frames, predictions, frame_index):
    score = float(predictions[frame_index])
    x_values = np.arange(frame_index + 1)
    artists["frame_image"].set_data(frames[frame_index])
    artists["progress_text"].set_text(
        f"FRAME {frame_index + 1:04d} / {len(frames):04d}"
    )
    artists["score_line"].set_data(x_values, predictions[: frame_index + 1])
    artists["score_marker"].set_data([frame_index], [score])
    fill_vertices = np.column_stack((x_values, predictions[: frame_index + 1]))
    fill_vertices = np.vstack(([0, 0], fill_vertices, [frame_index, 0]))
    artists["signal_fill"].set_xy(fill_vertices)
    artists["score_text"].set_text(f"{score:.3f}")
    elevated = score >= DISPLAY_THRESHOLD
    state_color = COLORS["danger"] if elevated else COLORS["green_bright"]
    artists["status_text"].set_text("ELEVATED" if elevated else "MONITORING")
    artists["status_text"].set_color(state_color)
    artists["status_text"].get_bbox_patch().set_edgecolor(state_color)
    for spine in artists["video_axis"].spines.values():
        spine.set_color(COLORS["danger"] if elevated else COLORS["line"])
    progress = (frame_index + 1) / len(frames)
    artists["timeline_progress"].set_xdata([0.07, 0.07 + 0.86 * progress])

    if artists["thumbnail_axes"]:
        nearest = int(
            np.argmin(np.abs(np.asarray(artists["shown_indices"]) - frame_index))
        )
        for index, axis in enumerate(artists["thumbnail_axes"]):
            active_color = COLORS["danger"] if elevated else COLORS["green_bright"]
            color = active_color if index == nearest else COLORS["line"]
            width = 1.8 if index == nearest else 0.8
            for spine in axis.spines.values():
                spine.set_color(color)
                spine.set_linewidth(width)

    return (
        artists["frame_image"],
        artists["progress_text"],
        artists["score_line"],
        artists["score_marker"],
        artists["score_text"],
        artists["signal_fill"],
        artists["status_text"],
        artists["timeline_progress"],
    )


def visualize_predictions(video_path, predictions, save_path, output_dir):
    frames = get_video_frames(video_path)
    predictions = np.asarray(predictions)
    if len(frames) != len(predictions):
        raise ValueError(
            f"frame count {len(frames)} does not match prediction count {len(predictions)}"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for stale_frame in output_path.glob("fr*.png"):
        stale_frame.unlink()
    plt.imsave(output_path / "thumbnail.png", frames[len(frames) // 2])

    anomaly_indices = [
        index
        for index in range(1, len(predictions))
        if predictions[index] - predictions[index - 1] > 0.05
    ]
    if len(anomaly_indices) >= 5:
        for output_index, frame_index in enumerate(anomaly_indices):
            plt.imsave(output_path / f"fr{output_index}.png", frames[frame_index])

    figure, artists = build_analysis_figure(frames, predictions, anomaly_indices)

    def update(frame_index):
        return _update_analysis_figure(artists, frames, predictions, frame_index)

    animation = FuncAnimation(
        figure, update, frames=range(0, len(frames), 10), interval=100, repeat=False
    )
    try:
        animation.save(save_path, writer=PillowWriter(fps=10), dpi=75)
    finally:
        plt.close(figure)
    return anomaly_indices
