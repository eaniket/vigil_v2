from pathlib import Path

from inference_service import InferenceService


BASE_DIR = Path(__file__).resolve().parent
DEMOS = [
    ("abuse", "Abuse029_x264.mp4"),
    ("arrest", "Arrest013_x264.mp4"),
    ("arson", "Arson049_x264.mp4"),
    ("assault", "Assault018_x264.mp4"),
    ("road-accident", "RoadAccidents027_x264.mp4"),
    ("burglary", "Burglary081_x264.mp4"),
    ("explosion", "Explosion034_x264.mp4"),
    ("fighting", "Fighting023_x264.mp4"),
    ("robbery", "Robbery089_x264.mp4"),
    ("shooting", "Shooting037_x264.mp4"),
    ("stealing", "Stealing095_x264.mp4"),
    ("shoplifting", "Shoplifting017_x264.mp4"),
    ("vandalism", "Vandalism032_x264.mp4"),
]


def main():
    service = InferenceService()
    for index, (slug, filename) in enumerate(DEMOS, start=1):
        video_path = BASE_DIR / "input" / filename
        output_dir = BASE_DIR / "public" / "output" / "demos" / slug
        required = [output_dir / "summary.json", output_dir / "out.gif", output_dir / "thumbnail.png"]
        if all(path.is_file() for path in required):
            print(f"[{index}/{len(DEMOS)}] {slug}: already generated")
            continue
        print(f"[{index}/{len(DEMOS)}] {slug}: analyzing {filename}")
        service.analyze(video_path, output_dir)
        print(f"[{index}/{len(DEMOS)}] {slug}: complete")


if __name__ == "__main__":
    main()
