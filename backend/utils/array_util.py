import numpy as np


def sliding_window(values, size, stride):
    if size <= 0 or stride <= 0:
        raise ValueError("size and stride must be positive")
    return [values[index : index + size] for index in range(0, len(values), stride)]


def chunks(values, size):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def interpolate(features, features_per_bag):
    features = np.asarray(features)
    if features.ndim != 2 or features.shape[0] == 0:
        raise ValueError("features must be a non-empty 2D array")
    if features_per_bag <= 0:
        raise ValueError("features_per_bag must be positive")
    interpolated = np.zeros((features_per_bag, features.shape[1]), dtype=np.float32)
    boundaries = np.round(np.linspace(0, len(features) - 1, num=features_per_bag + 1)).astype(int)
    for index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        if start == end:
            vector = features[start].astype(np.float32, copy=True)
        else:
            vector = np.mean(features[start : end + 1], axis=0, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if not np.isfinite(norm) or norm == 0:
            raise ValueError(f"feature bag {index} has an invalid norm: {norm}")
        interpolated[index] = vector / norm
    return interpolated


def extrapolate(outputs, num_frames):
    outputs = np.asarray(outputs)
    if outputs.size == 0:
        raise ValueError("outputs must not be empty")
    if num_frames <= 0:
        raise ValueError("num_frames must be positive")
    indices = np.round(np.linspace(0, len(outputs) - 1, num=num_frames)).astype(int)
    return outputs[indices]
