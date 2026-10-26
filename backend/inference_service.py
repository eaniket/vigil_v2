import shutil
import threading


class InferenceBusyError(RuntimeError):
    pass


class InferenceService:
    def __init__(self, model_loader=None, runner=None):
        self._model_loader = model_loader or self._load_default_models
        self._runner = runner or self._run_default
        self._models = None
        self._lock = threading.Lock()

    @staticmethod
    def _load_default_models():
        from c3d import c3d_feature_extractor
        from classifier import build_classifier_model

        return c3d_feature_extractor(), build_classifier_model()

    @staticmethod
    def _run_default(**kwargs):
        from demo import run_demo

        return run_demo(**kwargs)

    @property
    def is_busy(self):
        return self._lock.locked()

    @property
    def models_loaded(self):
        return self._models is not None

    def analyze(self, video_path, output_dir, cleanup_dir=None):
        if not self._lock.acquire(blocking=False):
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            raise InferenceBusyError("Another video is currently being analyzed")
        try:
            if self._models is None:
                self._models = self._model_loader()
            feature_extractor, classifier_model = self._models
            return self._runner(
                video_path=video_path,
                output_dir=output_dir,
                feature_extractor=feature_extractor,
                classifier_model=classifier_model,
            )
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            self._lock.release()
