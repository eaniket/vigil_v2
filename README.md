# Vigil

Vigil is a video-anomaly intelligence prototype for reviewing surveillance footage.
It combines a C3D-based anomaly-scoring pipeline, a Flask web application, themed
analysis visualizations, and Gemma-generated incident reports.

The project is designed as a research and product demo. Its output highlights
unusual visual changes for human review; it does not confirm that an incident
occurred or identify the people involved.

## What the project does

- Processes video with a C3D feature extractor and a trained anomaly classifier.
- Produces a frame-level anomaly score timeline.
- Generates a Vigil-themed animated dashboard (`out.gif`).
- Surfaces representative frames when strong score transitions are found.
- Provides 13 pre-generated surveillance scenarios in a browser-based Demo tab.
- Provides a simulated Test flow that waits seven seconds after file selection and
  displays a pre-generated sample analysis.
- Uses Google's hosted Gemma API to turn the selected result, thumbnail, and run
  metadata into a structured, cautious incident report.

Supported demo categories are Abuse, Arrest, Arson, Assault, Burglary, Explosion,
Fighting, Road Accident, Robbery, Shooting, Shoplifting, Stealing, and Vandalism.

## How it works

### Web demo flow

1. Flask loads the pre-generated results from `backend/public/output/`.
2. The user selects a scenario in the Demo tab or a local file in the Test tab.
3. The UI displays the corresponding animated analysis dashboard.
4. Flask sends the scenario thumbnail and run metadata to Gemma on demand.
5. Gemma returns a structured incident summary, observations, supporting evidence,
   recommended next steps, and uncertainty statement.
6. The report is cached for the lifetime of the Flask process. If Gemma is
   unavailable, the UI keeps a local fallback report.

The Test tab is intentionally simulated: the selected video remains in the browser
and is not uploaded. After seven seconds, the UI loads
`backend/public/output/sample_video/`.

### Video-classification flow

The separate command-line pipeline decodes a video, creates 16-frame clips, extracts
C3D features, runs the anomaly classifier, maps scores back to frames, and renders
the output artifacts.

## Repository structure

```text
vigil_new/
├── backend/
│   ├── app.py                    Flask application and API routes
│   ├── gemma_report_service.py   Gemma API integration
│   ├── demo.py                   Video-analysis CLI
│   ├── inference_service.py      C3D inference orchestration
│   ├── c3d.py / classifier.py    Model definitions
│   ├── templates/                Flask HTML templates
│   ├── public/static/            Deployed CSS and JavaScript
│   ├── public/output/            Pre-generated website results
│   ├── input/                    Sample anomaly videos
│   ├── trained_models/           Classifier files and C3D weights
│   └── tests/                    Web and inference tests
├── research.md                       Original-project research notes
└── plan.md                           Reorganization and validation plan
```

The legacy `Website/` directory is retained as reference material. The active UI is
served by Flask from `backend/templates/` and `backend/public/static/`.

## Requirements

- macOS or Linux
- Python 3.11 recommended for the complete ML pipeline
- A Google AI Studio API key for generated incident reports
- Approximately 5 GB of free disk space for the complete ML environment, model
  files, sample videos, and generated artifacts

The website can run without the ML dependencies because it uses pre-generated
outputs. Real video classification requires the full ML dependency set and model
weights.

## Run the website locally

All backend commands must be run from `backend/` because model and output paths are
relative to that directory.

### 1. Create the environment

```bash
cd backend
python3.11 -m venv vigil_env
source vigil_env/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-web.txt
```

If `vigil_env` already exists, only activate it:

```bash
cd backend
source vigil_env/bin/activate
```

### 2. Configure Gemma

Create an API key in Google AI Studio and expose it only through the environment:

```bash
export GEMINI_API_KEY="your-google-ai-studio-key"
```

The default model is `gemma-4-26b-a4b-it`. To use another supported Gemma model:

```bash
export GEMMA_MODEL="your-supported-gemma-model"
```

Do not add API keys to source files or commit them to Git. `.env` files are ignored,
but the application currently reads the key from the shell environment.

### 3. Start Flask

```bash
python3 -m flask --app app run --debug --host 127.0.0.1 --port 5050
```

Open <http://127.0.0.1:5050>.

Flask debug mode enables automatic reload for Python and template changes. Static
assets used by the active app are under `backend/public/static/`.

## Run real backend video classification

### 1. Install the ML dependencies

From `backend/` with `vigil_env` activated:

```bash
python3 -m pip install -r requirements-ml.txt
```

### 2. Verify the model files

The repository expects these classifier files:

```text
trained_models/model.json
trained_models/weights_L1L2.mat
```

Download the public C3D Sports-1M weights if they are not already present:

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

The C3D mean file is stored at `trained_models/c3d_mean.npy`. If it is absent, the
inference code downloads the checksum-verified file on first use.

### 3. Analyze a video

```bash
python3 demo.py --video input/in.mp4 --output-dir public/output/my-analysis
```

Use a different input path or output directory as needed. The output directory will
contain:

- `out.gif` — animated Vigil analysis dashboard.
- `predictions.npy` — anomaly score for each decoded frame.
- `summary.json` — duration, frame count, score range, and artifact metadata.
- `thumbnail.png` — preview used by the website.
- `fr*.png` — representative surfaced moments, when available.

To reproduce the original command format, use:

```bash
python3 demo.py --video input/in.mp4 --output-dir output
```

## Generate all 13 demo outputs

```bash
cd backend
source vigil_env/bin/activate
python3 generate_demos.py
python3 build_deployment_manifest.py
```

`generate_demos.py` skips complete results, so interrupted runs can be resumed. The
manifest command updates the metadata fallback used by serverless deployments.

## Run the tests

Install the full requirements first, then run:

```bash
cd backend
source vigil_env/bin/activate
python3 -m pip check
python3 -m pytest -q
```

The tests cover preprocessing, model loading and caching, artifact generation,
Flask routes, upload validation, Gemma report integration, cleanup, and output-file
security.

## Important limitations

- An anomaly score is not proof of a crime, emergency, or harmful event.
- Generated reports require human verification against the original footage.
- Gemma can make mistakes; the UI labels its reports as needing review.
- The Demo and Test tabs use pre-generated output and do not perform live inference.
- The current Flask workflow is intended for demonstration and research, not an
  unattended production surveillance system.
- Locations and camera IDs shown in the demo are fictional.

For backend-specific implementation notes, see
[`backend/README.md`](backend/README.md).
