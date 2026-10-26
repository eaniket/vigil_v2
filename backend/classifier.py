from pathlib import Path

import numpy as np
import scipy.io as sio
from tensorflow import keras

import configuration as cfg


def classifier_model():
    return keras.Sequential(
        [
            keras.Input(shape=(4096,)),
            keras.layers.Dense(512, kernel_initializer="glorot_normal", kernel_regularizer=keras.regularizers.l2(0.001), activation="relu"),
            keras.layers.Dropout(0.6),
            keras.layers.Dense(32, kernel_initializer="glorot_normal", kernel_regularizer=keras.regularizers.l2(0.001)),
            keras.layers.Dropout(0.6),
            keras.layers.Dense(1, kernel_initializer="glorot_normal", kernel_regularizer=keras.regularizers.l2(0.001), activation="sigmoid"),
        ],
        name="anomaly_classifier",
    )


def build_classifier_model():
    weights_path = Path(cfg.classifier_model_weights)
    if not weights_path.is_file():
        raise FileNotFoundError(f"Missing classifier weights: {weights_path}")
    return load_weights(classifier_model(), weights_path)


def convert_matlab_weights(matlab_data):
    converted = {}
    for index in range(len(matlab_data)):
        key = str(index)
        if key not in matlab_data:
            continue
        value = matlab_data[key]
        if value.shape == (0, 0):
            converted[key] = []
            continue
        layer_weights = []
        for weight in value[0]:
            if weight.ndim == 2 and weight.shape[0] == 1:
                weight = weight[0]
            layer_weights.append(np.asarray(weight))
        converted[key] = layer_weights
    return converted


def load_weights(model, weights_file):
    converted = convert_matlab_weights(sio.loadmat(weights_file))
    if len(model.layers) != len(converted):
        raise ValueError(
            f"Classifier layer count {len(model.layers)} does not match weight groups {len(converted)}"
        )
    for index, layer in enumerate(model.layers):
        layer.set_weights(converted[str(index)])
    return model


if __name__ == "__main__":
    build_classifier_model().summary()
