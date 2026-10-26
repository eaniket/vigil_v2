from pathlib import Path

import cv2

import parameters as params
from utils.array_util import sliding_window


def get_video_clips(video_path):
    frames = get_video_frames(video_path)
    return sliding_window(frames, params.frame_count, params.frame_count), len(frames)


def get_video_info(video_path):
    path = Path(video_path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open input video: {path}")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()
    return {"fps": fps, "reported_frame_count": frame_count}


def get_video_frames(video_path):
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input video does not exist: {path}")
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open input video: {path}")
    frames = []
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    finally:
        capture.release()
    if not frames:
        raise ValueError(f"No frames could be decoded from: {path}")
    return frames
