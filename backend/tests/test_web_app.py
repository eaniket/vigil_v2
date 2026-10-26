import io
import json
import shutil
from pathlib import Path

from app import create_app
from inference_service import InferenceBusyError


SUMMARY = {
    "analysis_file": "out.gif",
    "thumbnail_file": "thumbnail.png",
    "complete_clips": 2,
    "duration_seconds": 1.2,
    "fps": 30.0,
    "frame_count": 36,
    "score_max": 0.9,
    "score_min": 0.1,
    "surfaced_frame_files": ["fr0.png"],
    "surfaced_frame_indices": [12],
}


def write_result(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(SUMMARY))
    (directory / "out.gif").write_bytes(b"GIF89a")
    (directory / "thumbnail.png").write_bytes(b"PNG")
    (directory / "fr0.png").write_bytes(b"PNG")


class SuccessfulService:
    def analyze(self, _video_path, output_dir, cleanup_dir=None):
        write_result(Path(output_dir))
        if cleanup_dir:
            shutil.rmtree(cleanup_dir, ignore_errors=True)
        return SUMMARY


class BusyService:
    def analyze(self, _video_path, _output_dir, cleanup_dir=None):
        if cleanup_dir:
            shutil.rmtree(cleanup_dir, ignore_errors=True)
        raise InferenceBusyError("Another video is currently being analyzed")


class InvalidVideoService:
    def analyze(self, _video_path, _output_dir, cleanup_dir=None):
        raise ValueError("Video must contain at least 16 decodable frames")


class FailingService:
    def analyze(self, _video_path, _output_dir, cleanup_dir=None):
        raise RuntimeError("Unexpected inference failure")


class FakeGemmaReportService:
    def __init__(self):
        self.calls = []

    def generate(self, context, image_bytes=None):
        self.calls.append((context, image_bytes))
        return {
            "incident_summary": "Gemma-generated summary.",
            "timestamp": "00:00–00:01",
            "visual_observations": ["Observation one."],
            "supporting_evidence": ["Frame evidence."],
            "evidence_note": "Evidence note.",
            "recommended_next_steps": ["Review the footage."],
            "limitations": "Human review is required.",
        }


def make_app(tmp_path, service=None, max_size=100 * 1024 * 1024):
    output = tmp_path / "output"
    uploads = tmp_path / "uploads"
    app = create_app(
        {
            "TESTING": True,
            "OUTPUT_DIR": output,
            "UPLOAD_DIR": uploads,
            "INFERENCE_SERVICE": service or SuccessfulService(),
            "MAX_CONTENT_LENGTH": max_size,
            "DEPLOYMENT_MANIFEST": tmp_path / "missing-manifest.json",
            "USE_PREGENERATED_ANALYSIS": False,
        }
    )
    return app, output, uploads


def test_home_is_minimal_and_has_no_legacy_dependencies(tmp_path):
    app, _, _ = make_app(tmp_path)
    response = app.test_client().get("/")
    html = response.get_data(as_text=True).lower()
    assert response.status_code == 200
    assert "vigil" in html
    assert "panel-demo" in html and "panel-test" in html
    assert "dashboard-shell" in html
    assert 'data-tab-target="test"' in html
    assert 'data-tab-target="demo"' in html
    assert "data-sample-url" in html
    assert ">demo<" in html
    assert "workflow-grid" in html
    assert "detection-category" in html
    assert "detect supported anomaly categories" in html
    assert html.index("workflow-grid") < html.index("dashboard-shell")
    assert "evidence frames" not in html
    assert html.index("main-preview") < html.index("run-summary")
    assert "bootstrap" not in html
    assert "plotly" not in html
    assert "firebase" not in html
    assert "confirm incident" not in html
    assert "false positive" not in html


def test_demo_api_and_artifacts(tmp_path):
    app, output, _ = make_app(tmp_path)
    write_result(output)
    client = app.test_client()
    payload = client.get("/api/demo").get_json()
    assert payload["ready"] is True
    assert payload["summary"]["frame_count"] == 36
    assert client.get(payload["analysis_url"]).status_code == 200
    assert client.get(payload["frames"][0]["url"]).status_code == 200


def test_demo_api_handles_missing_output(tmp_path):
    app, _, _ = make_app(tmp_path)
    assert app.test_client().get("/api/demo").get_json() == {"ready": False}


def test_sample_analysis_api_returns_pre_generated_result(tmp_path):
    app, output, _ = make_app(tmp_path)
    sample = output / "sample_video"
    write_result(sample)
    app.config["PREGENERATED_ANALYSIS_DIR"] = sample
    response = app.test_client().get("/api/sample-analysis")
    assert response.status_code == 200
    assert response.get_json()["pre_generated"] is True
    assert response.get_json()["id"] == "sample_video"
    assert response.get_json()["analysis_url"].endswith("sample_video/out.gif")


def test_incident_report_uses_gemma_and_caches_result(tmp_path):
    gemma = FakeGemmaReportService()
    app, output, _ = make_app(tmp_path)
    write_result(output / "demos" / "assault")
    app.extensions["gemma_report_service"] = gemma
    client = app.test_client()

    first = client.post("/api/incident-report", json={"id": "assault"})
    second = client.post("/api/incident-report", json={"id": "assault"})

    assert first.status_code == 200
    assert first.get_json()["incident_report"]["incident_summary"] == "Gemma-generated summary."
    assert first.get_json()["cached"] is False
    assert second.get_json()["cached"] is True
    assert len(gemma.calls) == 1
    assert gemma.calls[0][0]["camera_id"] == "CAM-STREET-11"
    assert gemma.calls[0][1] == b"PNG"


def test_incident_report_rejects_unknown_result(tmp_path):
    app, _, _ = make_app(tmp_path)
    response = app.test_client().post("/api/incident-report", json={"id": "unknown"})
    assert response.status_code == 400


def test_demo_api_lists_pre_generated_class_runs(tmp_path):
    app, output, _ = make_app(tmp_path)
    write_result(output / "demos" / "abuse")
    write_result(output / "demos" / "assault")
    write_result(output / "demos" / "burglary")
    write_result(output / "demos" / "road-accident")
    write_result(output / "demos" / "shoplifting")
    payload = app.test_client().get("/api/demo").get_json()
    assert payload["ready"] is True
    assert [demo["label"] for demo in payload["demos"]] == [
        "Assault", "Burglary", "Shoplifting", "Abuse", "Road Accident"
    ]
    assert [demo["featured"] for demo in payload["demos"]] == [
        True, True, True, False, False
    ]
    assert "down on the pavement" in payload["demos"][0]["description"]
    assert payload["demos"][0]["camera_id"] == "CAM-STREET-11"
    assert payload["demos"][0]["location"] == "26 Mercer Walk, Riverside"
    assert all(demo["thumbnail_url"].endswith("thumbnail.png") for demo in payload["demos"])


def test_analyze_validates_upload(tmp_path):
    app, _, _ = make_app(tmp_path)
    client = app.test_client()
    assert client.post("/api/analyze").status_code == 400
    assert client.post(
        "/api/analyze", data={"video": (io.BytesIO(b""), "empty.mp4")}
    ).status_code == 400
    assert client.post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "sample.txt")}
    ).status_code == 400


def test_analyze_accepts_case_insensitive_video_and_cleans_upload(tmp_path):
    app, _, uploads = make_app(tmp_path)
    response = app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "Sample.MP4")}
    )
    assert response.status_code == 200
    assert response.get_json()["ready"] is True
    assert not uploads.exists() or not any(uploads.iterdir())


def test_analyze_can_return_pre_generated_sample_after_configured_delay(tmp_path):
    app, output, uploads = make_app(tmp_path)
    sample = output / "sample_video"
    write_result(sample)
    app.config.update(
        USE_PREGENERATED_ANALYSIS=True,
        PREGENERATED_ANALYSIS_DIR=sample,
        PREGENERATED_ANALYSIS_DELAY=0,
    )
    response = app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "sample.mp4")}
    )
    assert response.status_code == 200
    assert response.get_json()["pre_generated"] is True
    assert response.get_json()["analysis_url"].endswith("sample_video/out.gif")
    assert "ATM drive-through" in response.get_json()["description"]
    assert response.get_json()["camera_id"] == "CAM-ATM-01"
    assert not uploads.exists() or not any(uploads.iterdir())


def test_analyze_reports_busy_and_invalid_video(tmp_path):
    busy_app, _, _ = make_app(tmp_path / "busy", BusyService())
    busy = busy_app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "sample.mp4")}
    )
    assert busy.status_code == 409

    invalid_app, _, uploads = make_app(tmp_path / "invalid", InvalidVideoService())
    invalid = invalid_app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "sample.mp4")}
    )
    assert invalid.status_code == 400
    assert not uploads.exists() or not any(uploads.iterdir())


def test_analyze_rejects_oversized_request(tmp_path):
    app, _, _ = make_app(tmp_path, max_size=32)
    response = app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"x" * 128), "sample.mp4")}
    )
    assert response.status_code == 413


def test_analyze_handles_unexpected_failure_and_cleans_upload(tmp_path):
    app, _, uploads = make_app(tmp_path, FailingService())
    response = app.test_client().post(
        "/api/analyze", data={"video": (io.BytesIO(b"video"), "sample.mp4")}
    )
    assert response.status_code == 500
    assert response.get_json()["error"] == "Analysis failed. Check the server log and try again."
    assert not uploads.exists() or not any(uploads.iterdir())


def test_output_route_rejects_traversal(tmp_path):
    app, _, _ = make_app(tmp_path)
    assert app.test_client().get("/output/../app.py").status_code == 404
