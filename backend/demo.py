import argparse
import json
from pathlib import Path

import numpy as np

import configuration as cfg
import parameters as params
from c3d import c3d_feature_extractor, preprocess_input
from classifier import build_classifier_model
from utils.array_util import extrapolate, interpolate
from utils.video_util import get_video_clips, get_video_info
from utils.visualization_util import visualize_predictions


def write_summary(output_dir, summary):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    temporary_path = output_dir / "summary.json.tmp"
    temporary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_path.replace(summary_path)
    return summary_path


def build_summary(frame_count, complete_clips, fps, predictions, anomaly_indices):
    surfaced_indices = anomaly_indices if len(anomaly_indices) >= 5 else []
    return {
        "analysis_file": "out.gif",
        "thumbnail_file": "thumbnail.png",
        "complete_clips": int(complete_clips),
        "duration_seconds": round(frame_count / fps, 3) if fps > 0 else None,
        "fps": round(fps, 3) if fps > 0 else None,
        "frame_count": int(frame_count),
        "score_max": float(np.max(predictions)),
        "score_min": float(np.min(predictions)),
        "surfaced_frame_files": [
            f"fr{index}.png" for index in range(len(surfaced_indices))
        ],
        "surfaced_frame_indices": [int(index) for index in surfaced_indices],
    }


def run_demo(
    video_path=None,
    output_dir=None,
    feature_extractor=None,
    classifier_model=None,
):
    video_path = Path(video_path or cfg.sample_video_path)
    output_dir = Path(output_dir or cfg.output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_info = get_video_info(video_path)
    video_clips, num_frames = get_video_clips(video_path)
    complete_clips = [clip for clip in video_clips if len(clip) == params.frame_count]
    if not complete_clips:
        raise ValueError(f"Video must contain at least {params.frame_count} decodable frames")

    print(f"Decoded {num_frames} frames into {len(complete_clips)} complete clips")
    feature_extractor = feature_extractor or c3d_feature_extractor()
    classifier_model = classifier_model or build_classifier_model()
    print("Models initialized")

    rgb_features = []
    for index, clip in enumerate(complete_clips, start=1):
        processed_clip = preprocess_input(np.asarray(clip))
        rgb_features.append(feature_extractor.predict(processed_clip, verbose=0)[0])
        print(f"Processed clip {index}/{len(complete_clips)}")

    rgb_features = np.asarray(rgb_features)
    if not np.all(np.isfinite(rgb_features)):
        raise ValueError("C3D produced non-finite features")
    feature_bag = interpolate(rgb_features, params.features_per_bag)
    predictions = classifier_model.predict(feature_bag, verbose=0).squeeze()
    predictions = extrapolate(predictions, num_frames).astype(np.float32)
    if not np.all(np.isfinite(predictions)):
        raise ValueError("Classifier produced non-finite predictions")

    predictions_path = output_dir / "predictions.npy"
    np.save(predictions_path, predictions)
    gif_path = output_dir / "out.gif"
    anomaly_indices = visualize_predictions(video_path, predictions, gif_path, output_dir)
    summary = build_summary(
        num_frames,
        len(complete_clips),
        video_info["fps"],
        predictions,
        anomaly_indices,
    )
    write_summary(output_dir, summary)

    print(
        f"Inference complete: score range {predictions.min():.6f}–{predictions.max():.6f}; "
        f"{len(summary['surfaced_frame_indices'])} surfaced moments"
    )
    print(f"Predictions: {predictions_path}")
    print(f"Visualization: {gif_path}")
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Run Vigil video anomaly detection")
    parser.add_argument("--video", default=cfg.sample_video_path)
    parser.add_argument("--output-dir", default=cfg.output_folder)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run_demo(arguments.video, arguments.output_dir)
