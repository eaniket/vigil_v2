# Vigil Backend

Vigil is a local video-anomaly detection demo for Apple Silicon and Python 3.11. The website has two modes:

- **Demo** presents the pre-generated output in `public/output/`.
- **Test** accepts a local file selection, waits seven seconds in the browser, and
  displays the pre-generated `sample_video` result. The file is not uploaded.

There is no Firebase, database, authentication, or cloud upload. Real C3D inference
is available separately through the command-line workflow below.

## Setup

Run commands from this `backend/` directory because model/input/output paths are relative to it.

```bash
python3 -m venv vigil_env
source vigil_env/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-ml.txt
```

Download the public C3D Sports-1M weights:

```bash
curl -L --fail \
  https://github.com/adamcasson/c3d/releases/download/v0.1/sports1M_weights_tf.h5 \
  -o trained_models/c3d_sports1m.h5
shasum -a 256 trained_models/c3d_sports1m.h5
```

Expected SHA-256:

```text
c4d321e098d37c1585218dffe577c260f834fbbc8d9cb7950f0c3c165e1e93ce
```

The first inference downloads the checksum-verified 8.4 MB C3D mean array to `trained_models/c3d_mean.npy`.

## Run the website

Set a Google AI Studio key so Run Details can generate a report with Gemma. Keep
the key in the shell environment; do not add it to the repository.

```bash
source vigil_env/bin/activate
export GEMINI_API_KEY="your-google-ai-studio-key"
python3 -m flask --app app run --debug --host 127.0.0.1 --port 5050
```

Open <http://127.0.0.1:5050>. Debug mode automatically reloads Python,
template, and static-asset changes during local development.

The first time a result is displayed, Flask sends its thumbnail and run metadata
to `gemma-4-26b-a4b-it`. The generated structured incident report is cached for
the lifetime of the Flask process. If the API is unavailable, the UI keeps the
local fallback report and labels it accordingly. To select another supported
model, set `GEMMA_MODEL` before starting Flask.

### Demo tab

The Demo tab reads the pre-generated class gallery from `public/output/demos/<class>/`.
Generate or resume all 13 class demos with:

```bash
source vigil_env/bin/activate
python generate_demos.py
```

Each class directory contains:

- `summary.json`
- `out.gif`
- `thumbnail.png`
- `fr*.png` when score transitions are surfaced

The batch command skips complete class outputs, so it can safely resume after interruption.

### Test tab

- Accepted formats: MP4, MOV, AVI, and MKV.
- Maximum upload: 100 MB.
- The local website runs a seven-second browser timer and then displays the
  pre-generated result from `public/output/sample_video/`.
- The selected source file stays in the browser and is not uploaded to Flask.
- Live C3D inference remains available through the CLI commands below.

This synchronous, single-user workflow is intended for a local demonstration, not public deployment.

## Run inference from the CLI

```bash
source vigil_env/bin/activate
python3 demo.py --video input/in.mp4 --output-dir public/output
```

The command creates:

- `predictions.npy`: one anomaly score per decoded frame.
- `out.gif`: a 16:9 Vigil-themed analysis dashboard with the monitored video,
  detected-moment thumbnails, live confidence, and the evolving anomaly signal.
- `fr*.png`: surfaced frames when at least five score increases exceed `0.05`.
- `summary.json`: web-readable run metadata and artifact names.

The included 1,159-frame video was validated locally. It produces 72 complete clips, 1,159 finite scores, a readable 116-frame GIF, and six surfaced moments.

The GIF renderer uses the same black-green visual language as the web interface.
Its left column contains the monitored video and up to six representative detected
moments; its right column contains the live score, review threshold, signal graph,
model label, and timeline progress. Videos with fewer than five score increases show
a `No detected moments` state and keep the rest of the dashboard intact.

## Local result cleanup

Inspect generated Test runs before deleting anything:

```bash
find public/output/runs -mindepth 1 -maxdepth 1 -type d -print
```

Remove only a specific run you no longer need:

```bash
rm -rf public/output/runs/<job-id>
```

The root pre-generated Demo output is separate and is not removed by deleting a Test run.

## Validation

```bash
source vigil_env/bin/activate
python3 -m pip check
python3 -m compileall -q .
python3 -m pytest -q
```

The test suite covers ML preprocessing/model loading, summary generation, model caching, upload validation, cleanup, busy handling, generated artifact routes, and path traversal rejection.
