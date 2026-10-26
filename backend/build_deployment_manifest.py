import json
from pathlib import Path

from app import RUN_CONTEXT, RUN_DESCRIPTIONS, incident_report


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = BASE_DIR / "public" / "output"


def artifact_payload(directory, slug):
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    base_url = f"/output/{directory.relative_to(OUTPUT_ROOT).as_posix()}"
    frames = [
        {
            "frame_index": frame_index,
            "label": f"Moment {index + 1:02d}",
            "url": f"{base_url}/{filename}",
        }
        for index, (filename, frame_index) in enumerate(
            zip(
                summary.get("surfaced_frame_files", []),
                summary.get("surfaced_frame_indices", []),
            )
        )
    ]
    location, camera_id = RUN_CONTEXT[slug]
    description = RUN_DESCRIPTIONS[slug]
    return {
        "analysis_url": f"{base_url}/{summary.get('analysis_file', 'out.gif')}",
        "camera_id": camera_id,
        "description": description,
        "incident_report": incident_report(slug, summary, description, frames),
        "frames": frames,
        "location": location,
        "ready": True,
        "summary": summary,
        "thumbnail_url": f"{base_url}/{summary.get('thumbnail_file', 'thumbnail.png')}",
    }


def main():
    featured = ["assault", "burglary", "shoplifting"]
    demo_root = OUTPUT_ROOT / "demos"
    slugs = featured + sorted(path.name for path in demo_root.iterdir() if path.name not in featured)
    demos = []
    for slug in slugs:
        payload = artifact_payload(demo_root / slug, slug)
        payload.update(
            featured=slug in featured,
            id=slug,
            label=slug.replace("-", " ").title(),
        )
        demos.append(payload)
    manifest = {
        "demos": demos,
        "sample": artifact_payload(OUTPUT_ROOT / "sample_video", "sample_video"),
    }
    (BASE_DIR / "deployment_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
