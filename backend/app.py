import json
import logging
import shutil
import time
import uuid
from pathlib import Path

from flask import Flask, current_app, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from inference_service import InferenceBusyError, InferenceService
from gemma_report_service import GemmaReportError, GemmaReportService


BASE_DIR = Path(__file__).resolve().parent
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
RUN_DESCRIPTIONS = {
    "abuse": "A dark-clothed person moves through a residential driveway beside closely parked SUVs. The abrupt activity near the vehicles creates the strongest visual transition.",
    "arrest": "A marked patrol car stops along a wet residential road near a gated entrance. Vehicle arrival and roadside movement drive the elevated segment.",
    "arson": "A sudden, intense burst of flame fills a dim indoor camera view. The rapid brightness expansion and obscured surroundings produce a sharp anomaly response.",
    "assault": "A person is down on the pavement beside a parked van while another figure remains nearby. The fall and close-range movement form the key review moment.",
    "burglary": "Movement appears along a narrow residential driveway between two houses. The subject enters a normally quiet side-yard area close to doors and bins.",
    "explosion": "A distant industrial structure emits a fast-rising plume visible against the sky. The sudden change in scale and density dominates the frame sequence.",
    "fighting": "Two people engage in a close physical confrontation inside a building entrance. Rapid arm movement and changing body positions trigger the anomaly signal.",
    "road-accident": "Traffic crosses a city intersection as a yellow taxi enters the monitored area. The unusual vehicle motion develops near the crossing and roadside signs.",
    "robbery": "A person in light clothing bends close to another individual beside a vehicle. Their compressed posture and abrupt interaction create the primary review window.",
    "shooting": "Two vehicles converge on a roadway in a low-resolution camera view. Their sudden approach and close positioning correspond with the strongest detected change.",
    "shoplifting": "A shopper moves behind a crowded retail counter surrounded by small merchandise. Reaching and body movement within the restricted counter area drive the alert.",
    "stealing": "A lone person stands near a parked dark vehicle on a narrow street. Movement around the vehicle and repeated proximity create the surfaced anomaly interval.",
    "vandalism": "A person approaches parked cars during a low-light street recording. Activity close to the vehicle exterior produces the most notable frame transition.",
    "sample_video": "A vehicle enters the ATM drive-through as a person moves abruptly near the curb and machine. The close vehicle-person interaction produces the strongest anomaly spike.",
}
DEFAULT_RUN_DESCRIPTION = (
    "Vigil detected rapid visual changes in this footage. Review the highlighted timeline "
    "and monitored frames to determine the event context."
)
RUN_CONTEXT = {
    "abuse": ("1842 Cedar Hollow Dr, Brookfield", "CAM-DRIVE-04"),
    "arrest": ("77 Westhaven Rd, Northgate", "CAM-GATE-02"),
    "arson": ("410 Foundry Lane, East Junction", "CAM-WAREHOUSE-07"),
    "assault": ("26 Mercer Walk, Riverside", "CAM-STREET-11"),
    "burglary": ("903 Alder Court, Fairview", "CAM-SIDEYARD-03"),
    "explosion": ("12 Harbor Industrial Way, Port District", "CAM-SKYLINE-01"),
    "fighting": ("155 Union Plaza, Midtown", "CAM-LOBBY-06"),
    "road-accident": ("8 Market & Grand Ave, Central City", "CAM-TRAFFIC-14"),
    "robbery": ("342 Station Road, Southbank", "CAM-ALLEY-05"),
    "shooting": ("61 Ridgeway Blvd, West End", "CAM-ROAD-09"),
    "shoplifting": ("220 Greenfield Mall, Lakeside", "CAM-RETAIL-12"),
    "stealing": ("49 Old Mill Street, Stonebridge", "CAM-PARKING-08"),
    "vandalism": ("731 Elm Terrace, Hillcrest", "CAM-FRONT-03"),
    "sample_video": ("101 Capital Plaza, River District", "CAM-ATM-01"),
}
DEFAULT_RUN_CONTEXT = ("Local demonstration upload", "CAM-LOCAL-01")

ROAD_ACCIDENT_REPORT = {
    "timestamp": "14:32:08–14:32:15",
    "visual_observations": [
        "Two vehicles converge at the intersection.",
        "A sudden contact-like movement is visible.",
        "One vehicle remains stationary afterward.",
    ],
    "supporting_evidence": [
        "Frame at 14:32:09 — vehicles approaching.",
        "Frame at 14:32:11 — apparent contact.",
        "Frame at 14:32:14 — vehicle stopped.",
    ],
    "limitations": (
        "The footage supports a possible collision. Injuries, intent, fault, and the "
        "identities of the people involved are not established."
    ),
}


def incident_report(slug, summary, description, frames):
    """Build a cautious, review-oriented incident report for the result UI."""
    if slug == "road-accident":
        details = ROAD_ACCIDENT_REPORT
        incident_summary = (
            "A vehicle appears to collide with a second vehicle at an intersection. "
            "One vehicle stops immediately after the apparent impact. The available "
            "frames suggest a possible road accident, but injuries and the full sequence "
            "of events cannot be confirmed from the provided evidence."
        )
    else:
        duration = float(summary.get("duration_seconds", 0) or 0)
        details = {
            "timestamp": f"00:00–{int(duration // 60):02d}:{int(duration % 60):02d}",
            "visual_observations": [
                description,
                "The anomaly score changes most strongly during the surfaced interval.",
                "The surrounding footage should be reviewed to establish the full sequence.",
            ],
            "supporting_evidence": [
                f"{frame['label']} — flagged at frame {frame['frame_index']}."
                for frame in frames[:3]
                if frame.get("frame_index") is not None
            ] or ["The generated analysis visualization identifies the strongest score transition."],
            "limitations": (
                "The footage indicates a possible anomalous event, but intent, identities, "
                "causation, and consequences cannot be established from these frames alone."
            ),
        }
        incident_summary = description

    return {
        "incident_summary": incident_summary,
        "timestamp": details["timestamp"],
        "visual_observations": details["visual_observations"],
        "supporting_evidence": details["supporting_evidence"],
        "evidence_note": (
            "Illustrative timestamps; actual evidence should link to saved frames from the video."
        ),
        "recommended_next_steps": [
            "Review the original footage around the flagged interval.",
            "If the event is confirmed, notify the designated response team according to local protocol.",
            "Check adjacent camera feeds for additional context, if authorized.",
        ],
        "limitations": details["limitations"],
    }


def result_payload(result_dir, output_root):
    result_dir = Path(result_dir)
    output_root = Path(output_root)
    summary_path = result_dir / "summary.json"
    if not summary_path.is_file():
        return {"ready": False}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        current_app.logger.exception("Could not read result summary: %s", summary_path)
        return {"ready": False}
    try:
        relative_dir = result_dir.resolve().relative_to(output_root.resolve())
    except ValueError:
        return {"ready": False}

    analysis_file = summary.get("analysis_file", "out.gif")
    if Path(analysis_file).name != analysis_file or not (result_dir / analysis_file).is_file():
        return {"ready": False}

    def artifact_url(filename):
        return url_for(
            "output_file", filename=(relative_dir / filename).as_posix()
        )

    thumbnail_file = summary.get("thumbnail_file", "thumbnail.png")
    thumbnail_url = (
        artifact_url(thumbnail_file)
        if Path(thumbnail_file).name == thumbnail_file
        and (result_dir / thumbnail_file).is_file()
        else artifact_url(analysis_file)
    )

    frames = []
    frame_files = summary.get("surfaced_frame_files", [])
    frame_indices = summary.get("surfaced_frame_indices", [])
    for position, filename in enumerate(frame_files):
        if Path(filename).name != filename or not (result_dir / filename).is_file():
            continue
        frame_index = frame_indices[position] if position < len(frame_indices) else None
        frames.append(
            {
                "frame_index": frame_index,
                "label": f"Moment {position + 1:02d}",
                "url": artifact_url(filename),
            }
        )
    slug = result_dir.name
    location, camera_id = RUN_CONTEXT.get(slug, DEFAULT_RUN_CONTEXT)
    description = RUN_DESCRIPTIONS.get(slug, DEFAULT_RUN_DESCRIPTION)
    return {
        "analysis_url": artifact_url(analysis_file),
        "camera_id": camera_id,
        "description": description,
        "incident_report": incident_report(slug, summary, description, frames),
        "frames": frames,
        "location": location,
        "ready": True,
        "summary": summary,
        "thumbnail_url": thumbnail_url,
    }


def create_app(config=None):
    app = Flask(__name__, static_folder="public/static", static_url_path="/static")
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,
        DEPLOYMENT_MANIFEST=BASE_DIR / "deployment_manifest.json",
        OUTPUT_DIR=BASE_DIR / "public" / "output",
        PREGENERATED_ANALYSIS_DELAY=7,
        PREGENERATED_ANALYSIS_DIR=BASE_DIR / "public" / "output" / "sample_video",
        SEND_FILE_MAX_AGE_DEFAULT=0,
        TEMPLATES_AUTO_RELOAD=True,
        UPLOAD_DIR=BASE_DIR / "runtime" / "uploads",
        USE_PREGENERATED_ANALYSIS=True,
    )
    if config:
        app.config.update(config)
    app.extensions["inference_service"] = app.config.get(
        "INFERENCE_SERVICE", InferenceService()
    )
    app.extensions["gemma_report_service"] = app.config.get(
        "GEMMA_REPORT_SERVICE", GemmaReportService()
    )
    app.extensions["gemma_report_cache"] = {}

    @app.get("/")
    def index():
        return render_template("home.html")

    @app.get("/api/demo")
    def demo_result():
        output_root = Path(app.config["OUTPUT_DIR"])
        demo_root = output_root / "demos"
        demos = []
        if demo_root.is_dir():
            featured = {"assault": 0, "burglary": 1, "shoplifting": 2}
            directories = sorted(
                (path for path in demo_root.iterdir() if path.is_dir()),
                key=lambda path: (featured.get(path.name, len(featured)), path.name),
            )
            for directory in directories:
                payload = result_payload(directory, output_root)
                if not payload.get("ready"):
                    continue
                payload["id"] = directory.name
                payload["label"] = directory.name.replace("-", " ").title()
                payload["featured"] = directory.name in featured
                demos.append(payload)
        if demos:
            return jsonify(ready=True, demos=demos)
        manifest_path = Path(app.config["DEPLOYMENT_MANIFEST"])
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return jsonify(ready=True, demos=manifest["demos"])
        return jsonify(result_payload(output_root, output_root))

    @app.get("/api/sample-analysis")
    def sample_analysis():
        payload = result_payload(
            app.config["PREGENERATED_ANALYSIS_DIR"],
            app.config["OUTPUT_DIR"],
        )
        if not payload.get("ready"):
            manifest_path = Path(app.config["DEPLOYMENT_MANIFEST"])
            if not manifest_path.is_file():
                return jsonify(error="The pre-generated sample analysis is unavailable."), 404
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload = manifest["sample"]
        payload["pre_generated"] = True
        payload["id"] = "sample_video"
        return jsonify(payload)

    @app.post("/api/incident-report")
    def generate_incident_report():
        body = request.get_json(silent=True) or {}
        run_id = body.get("id")
        allowed_ids = set(RUN_DESCRIPTIONS)
        if run_id not in allowed_ids:
            return jsonify(error="Unknown analysis result."), 400

        cache = app.extensions["gemma_report_cache"]
        if run_id in cache:
            return jsonify(generated=True, cached=True, incident_report=cache[run_id])

        output_root = Path(app.config["OUTPUT_DIR"])
        result_dir = (
            Path(app.config["PREGENERATED_ANALYSIS_DIR"])
            if run_id == "sample_video"
            else output_root / "demos" / run_id
        )
        payload = result_payload(result_dir, output_root)
        if not payload.get("ready"):
            manifest_path = Path(app.config["DEPLOYMENT_MANIFEST"])
            if not manifest_path.is_file():
                return jsonify(error="Analysis evidence is unavailable."), 404
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload = (
                manifest["sample"]
                if run_id == "sample_video"
                else next((item for item in manifest["demos"] if item["id"] == run_id), {})
            )
        if not payload:
            return jsonify(error="Analysis evidence is unavailable."), 404

        thumbnail_path = result_dir / payload.get("summary", {}).get(
            "thumbnail_file", "thumbnail.png"
        )
        image_bytes = thumbnail_path.read_bytes() if thumbnail_path.is_file() else None
        context = {
            "scenario_hypothesis": run_id.replace("-", " "),
            "location": payload["location"],
            "camera_id": payload["camera_id"],
            "duration_seconds": payload["summary"].get("duration_seconds"),
            "frame_count": payload["summary"].get("frame_count"),
            "peak_anomaly_score": payload["summary"].get("score_max"),
            "surfaced_frames": [frame.get("frame_index") for frame in payload.get("frames", [])],
        }
        try:
            report = app.extensions["gemma_report_service"].generate(
                context, image_bytes=image_bytes
            )
        except GemmaReportError as error:
            app.logger.warning("Gemma report generation failed for %s: %s", run_id, error)
            return jsonify(error=str(error), incident_report=payload["incident_report"]), 502
        cache[run_id] = report
        return jsonify(generated=True, cached=False, incident_report=report)

    @app.post("/api/analyze")
    def analyze_video():
        if "video" not in request.files:
            return jsonify(error="Choose a video file to analyze."), 400
        uploaded_file = request.files["video"]
        if not uploaded_file.filename:
            return jsonify(error="Choose a video file to analyze."), 400
        extension = Path(uploaded_file.filename).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            return jsonify(error="Unsupported video type. Use MP4, MOV, AVI, or MKV."), 400

        job_id = uuid.uuid4().hex
        upload_dir = Path(app.config["UPLOAD_DIR"]) / job_id
        output_dir = Path(app.config["OUTPUT_DIR"]) / "runs" / job_id
        upload_dir.mkdir(parents=True, exist_ok=False)
        video_path = upload_dir / f"source{extension}"
        uploaded_file.save(video_path)
        if video_path.stat().st_size == 0:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify(error="The uploaded video is empty."), 400

        if app.config["USE_PREGENERATED_ANALYSIS"]:
            try:
                time.sleep(app.config["PREGENERATED_ANALYSIS_DELAY"])
                payload = result_payload(
                    app.config["PREGENERATED_ANALYSIS_DIR"],
                    app.config["OUTPUT_DIR"],
                )
                if not payload.get("ready"):
                    return jsonify(error="The pre-generated sample analysis is unavailable."), 500
                payload["job_id"] = job_id
                payload["pre_generated"] = True
                return jsonify(payload)
            finally:
                shutil.rmtree(upload_dir, ignore_errors=True)

        service = app.extensions["inference_service"]
        try:
            service.analyze(video_path, output_dir, cleanup_dir=upload_dir)
        except InferenceBusyError as error:
            return jsonify(error=str(error)), 409
        except (FileNotFoundError, ValueError) as error:
            shutil.rmtree(output_dir, ignore_errors=True)
            return jsonify(error=str(error)), 400
        except Exception:
            shutil.rmtree(output_dir, ignore_errors=True)
            app.logger.exception("Video analysis failed for job %s", job_id)
            return jsonify(error="Analysis failed. Check the server log and try again."), 500
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)

        payload = result_payload(output_dir, app.config["OUTPUT_DIR"])
        payload["job_id"] = job_id
        return jsonify(payload)

    @app.get("/output/<path:filename>")
    def output_file(filename):
        return send_from_directory(app.config["OUTPUT_DIR"], filename)

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        return jsonify(error="Video is too large. The maximum size is 100 MB."), 413

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=True)
