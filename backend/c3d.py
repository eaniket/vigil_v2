from pathlib import Path

import cv2
import numpy as np
from tensorflow import keras

import configuration as cfg


C3D_MEAN_URL = "https://github.com/adamcasson/c3d/releases/download/v0.1/c3d_mean.npy"
C3D_MEAN_MD5 = "08a07d9761e76097985124d9e8b2fe34"


def get_c3d_mean_path():
    mean_path = Path(cfg.c3d_mean)
    if mean_path.is_file():
        return mean_path
    downloaded_path = keras.utils.get_file(
        fname=mean_path.name,
        origin=C3D_MEAN_URL,
        file_hash=C3D_MEAN_MD5,
        hash_algorithm="md5",
        cache_dir=str(mean_path.parent.parent.resolve()),
        cache_subdir=mean_path.parent.name,
    )
    return Path(downloaded_path)


def preprocess_input(video, mean_path=None):
    video = np.asarray(video)
    if video.ndim != 4 or video.shape[-1] != 3:
        raise ValueError("video must have shape (frames, height, width, 3)")
    if video.shape[0] < 16:
        raise ValueError("C3D preprocessing requires at least 16 frames")

    intervals = np.ceil(np.linspace(0, video.shape[0] - 1, 16)).astype(int)
    frames = video[intervals]
    resized_frames = np.empty((16, 128, 171, 3), dtype=np.float32)
    for index, frame in enumerate(frames):
        resized_frames[index] = cv2.resize(
            frame, (171, 128), interpolation=cv2.INTER_CUBIC
        )

    resolved_mean_path = Path(mean_path) if mean_path else get_c3d_mean_path()
    mean = np.load(resolved_mean_path)
    if mean.shape != resized_frames.shape:
        raise ValueError(
            f"C3D mean shape {mean.shape} does not match {resized_frames.shape}"
        )
    resized_frames -= mean
    cropped_frames = resized_frames[:, 8:120, 30:142, :]
    return np.expand_dims(cropped_frames, axis=0)


def C3D(weights="sports1M"):
    if weights not in {"sports1M", None}:
        raise ValueError("weights must be either 'sports1M' or None")

    model = keras.Sequential(
        [
            keras.Input(shape=(16, 112, 112, 3)),
            keras.layers.Conv3D(64, 3, activation="relu", padding="same", name="conv1"),
            keras.layers.MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2), padding="same", name="pool1"),
            keras.layers.Conv3D(128, 3, activation="relu", padding="same", name="conv2"),
            keras.layers.MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name="pool2"),
            keras.layers.Conv3D(256, 3, activation="relu", padding="same", name="conv3a"),
            keras.layers.Conv3D(256, 3, activation="relu", padding="same", name="conv3b"),
            keras.layers.MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name="pool3"),
            keras.layers.Conv3D(512, 3, activation="relu", padding="same", name="conv4a"),
            keras.layers.Conv3D(512, 3, activation="relu", padding="same", name="conv4b"),
            keras.layers.MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name="pool4"),
            keras.layers.Conv3D(512, 3, activation="relu", padding="same", name="conv5a"),
            keras.layers.Conv3D(512, 3, activation="relu", padding="same", name="conv5b"),
            keras.layers.ZeroPadding3D(padding=(0, 1, 1)),
            keras.layers.MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name="pool5"),
            keras.layers.Flatten(),
            keras.layers.Dense(4096, activation="relu", name="fc6"),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(4096, activation="relu", name="fc7"),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(487, activation="softmax", name="fc8"),
        ],
        name="c3d",
    )
    if weights == "sports1M":
        weights_path = Path(cfg.c3d_model_weights)
        if not weights_path.is_file():
            raise FileNotFoundError(
                f"Missing C3D weights: {weights_path}. See backend/README.md."
            )
        model.load_weights(weights_path)
    return model


def c3d_feature_extractor():
    model = C3D()
    return keras.Model(
        inputs=model.inputs,
        outputs=model.get_layer("fc6").output,
        name="c3d_fc6_feature_extractor",
    )
