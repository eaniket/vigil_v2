# Backend and Anomaly Detection Reorganization Plan

> I want to build a new feature `a dedicated backend folder containing the Flask backend and anomaly-detection system` that extends the system to perform `clear separation between the standalone frontend and the runnable Python backend, with documented backend startup commands`.

## Feature summary and business outcome

Reorganize the repository so all executable Python backend code and anomaly-detection runtime assets live under one `backend/` directory. The result should make the project layout understandable, give the backend a single working directory, and provide explicit commands for running the safe local Flask mode and, separately, the legacy anomaly pipeline.

This is a structural refactor, not a model rewrite or Firebase modernization. Existing behavior should remain unchanged except for import/path adjustments required by the move.

## Current-state summary

The repository currently mixes several concerns at its root:

- Flask backend: `app.py`, `db.py`, `db_web.py`, `templates/`, and `static/`.
- Anomaly detection: `demo.py`, `c3d.py`, `classifier.py`, `configuration.py`, `parameters.py`, and `utils/`.
- Runtime/model assets: `input/`, `output/`, and `trained_models/`.
- Standalone frontend/export: `Website/` and `Website.zip`.
- Research/data artifacts: `data.csv` and `Temporal_Anomaly_Annotation_For_Testing_Videos/`.

The backend currently runs safely in local mode with:

```bash
python3 -m flask --app app run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
```

Live Firebase services are gated by `VIGIL_ENABLE_LIVE_SERVICES=1`. The actual ML pipeline cannot yet run on the current Apple Silicon/Python 3.11 environment because it targets TensorFlow 1.10/Keras 2.2, uses removed SciPy/Keras APIs, and is missing `trained_models/c3d_sports1m.h5`.

## Proposed directory structure

```text
vigil_new/
├── backend/
│   ├── app.py
│   ├── db.py
│   ├── db_web.py
│   ├── demo.py
│   ├── c3d.py
│   ├── classifier.py
│   ├── configuration.py
│   ├── parameters.py
│   ├── requirements-web.txt
│   ├── README.md
│   ├── utils/
│   ├── templates/
│   ├── static/
│   ├── trained_models/
│   ├── input/
│   └── output/
├── Website/
├── Website.zip
├── Temporal_Anomaly_Annotation_For_Testing_Videos/
├── data.csv
├── README.md
├── research.md
└── plan.md
```

The annotation dataset and `data.csv` will remain at the root because the active backend does not read them. They are research/source artifacts rather than runtime dependencies. `Website/` remains at the root as the standalone frontend/export.

## Proposed technical approach

### 1. Move backend runtime files as one unit

Move the following into `backend/`:

- Python entry points and integrations: `app.py`, `db.py`, `db_web.py`, `demo.py`.
- ML implementation/configuration: `c3d.py`, `classifier.py`, `configuration.py`, `parameters.py`, `utils/`.
- Flask assets: `templates/`, `static/`.
- Model and media assets: `trained_models/`, `input/`, `output/`.

Do not move generated Python bytecode. Remove the checked-in/copied root `__pycache__/` directory from the working tree and add Python cache patterns to `.gitignore`.

### 2. Preserve the backend working-directory contract

The legacy configuration uses paths such as `./input/in.mp4` and `./trained_models/...`. The least invasive approach is to document that backend commands must run from `backend/`.

```bash
cd backend
python3 -m flask --app app run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
```

This avoids rewriting every model/media path during a structural-only change.

### 3. Repair the one cross-boundary frontend asset reference

The current Flask app serves dashboard icons from root-level `Website/`. After moving `app.py`, a relative `Website` path would incorrectly resolve to `backend/Website`.

Prefer removing that cross-boundary route and making Flask self-contained:

- Move/copy the three icons used by Flask into `backend/static/images/`.
- Change the template icon URLs to Flask static URLs.
- Remove the `/website-assets/<path:filename>` route and its `send_from_directory` import.
- Leave the original icons in `Website/` because that standalone frontend also needs them.

Expected template pattern:

```html
<img src="{{ url_for('static', filename='images/police.png') }}" alt="Police">
```

This is intentional duplication at a deployment boundary: the standalone frontend and Flask application each own the assets they serve.

### 4. Add a minimal web dependency manifest

Add `backend/requirements-web.txt` for safe local Flask mode only:

```text
Flask==3.0.3
requests==2.33.1
```

Do not claim the legacy anomaly stack is installable on Python 3.11. Document its historical pins separately in the backend README and state the missing C3D weights requirement.

A full modern ML dependency file should be created only as part of a dedicated model-porting feature, after compatibility work and output validation.

### 5. Document backend execution modes

Add `backend/README.md` with three clearly separated modes:

1. **Safe local Flask mode** — install `requirements-web.txt` and run the UI without Firebase writes or ML imports.
2. **Live Firebase mode** — explain required environment variables and warn that it sends notifications/uploads to external services. Do not include credential values.
3. **Legacy anomaly demo** — document the historical dependency versions, ImageMagick requirement, missing C3D weight file, and `python demo.py` command, while clearly stating it is not expected to run on the current Python 3.11 Apple Silicon environment without a port or legacy machine/container.

Update the root `README.md` into a repository map that points users to `backend/README.md` and distinguishes `backend/` from `Website/`.

### 6. Keep safe mode as the default

The refactor must preserve the existing safe startup behavior:

- Importing `app.py` must not require TensorFlow/Keras/Pyrebase/python-firebase.
- `POST /test` must not access Firebase unless `VIGIL_ENABLE_LIVE_SERVICES=1`.
- Live mode must continue to require `VIGIL_FCM_SERVER_KEY` from the environment.

## Files and modules to create, move, or modify

### Create

- `backend/`
- `backend/README.md`
- `backend/requirements-web.txt`
- `backend/static/images/police.png`
- `backend/static/images/hospital.png`
- `backend/static/images/fire.png`

### Move into `backend/`

- `app.py`
- `db.py`
- `db_web.py`
- `demo.py`
- `c3d.py`
- `classifier.py`
- `configuration.py`
- `parameters.py`
- `utils/`
- `templates/`
- `static/`
- `trained_models/`
- `input/`
- `output/`

### Modify

- `backend/app.py`: remove the temporary root `Website/` asset route.
- `backend/templates/test.html`: use backend static icon URLs.
- `.gitignore`: ignore Python caches and preserve the new C3D weight path.
- Root `README.md`: describe repository layout and link to backend instructions.
- `research.md`: update paths and note the completed separation after implementation.
- `plan.md`: receive the detailed todo checklist and completion marks in later phases.

### Leave at repository root

- `Website/` and `Website.zip`.
- `data.csv`.
- `Temporal_Anomaly_Annotation_For_Testing_Videos/`.
- `research.md` and `plan.md`.

## API, data model, UI, and integration impact

- **HTTP routes:** no route contract changes; `/`, `POST /test`, and Flask static URLs remain.
- **Firebase schema:** no changes.
- **FCM payload:** no changes.
- **Model architecture and inference:** no changes.
- **Frontend behavior:** dashboard icons become Flask-owned static assets; standalone `Website/` stays intact.
- **Command location:** backend commands must run from `backend/`.
- **Data/assets:** runtime input/output/model assets move with the backend; unrelated dataset artifacts remain at root.

## Error handling and validation strategy

- Preserve safe local mode so missing ML/Firebase packages do not prevent Flask startup.
- Verify the Flask app imports from within `backend/` on Python 3.11.
- Use Flask's test client to validate `GET /`, local-mode `POST /test`, CSS, JavaScript, and all three icons.
- Confirm local-mode rendered HTML does not include the live Firebase integration script and keeps live-action buttons disabled.
- Confirm `configuration.py` paths resolve when the current directory is `backend/`.
- Confirm no Python import still relies on a module left at repository root.
- Do not run live Firebase mode during validation.
- Do not execute legacy model inference until compatible dependencies and `c3d_sports1m.h5` are available.

## Typecheck, test, and manual verification strategy

There is no configured type checker or automated test suite. Validation will therefore use:

```bash
cd backend
python3 -m compileall -q .
python3 -c "from app import app; print(app.url_map)"
python3 -m flask --app app run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
```

And targeted Flask test-client checks:

```python
from app import app

client = app.test_client()
assert client.get('/').status_code == 200
assert client.post('/test', data={'action': 'CONFIRM'}).status_code == 200
assert client.get('/static/css/styles.css').status_code == 200
assert client.get('/static/images/police.png').status_code == 200
```

Manual verification will open the local server, submit the home form, and confirm the dashboard, styling, Plotly map, and icons render without enabling Firebase.

## Risks and tradeoffs

- Running from the repository root with `--app backend/app.py` would leave legacy relative paths pointing at root-level `input/` and `trained_models/`. Requiring `cd backend` is simpler and will be documented explicitly.
- Duplicating three small icons between `Website/` and `backend/static/images/` avoids coupling two separately served frontends.
- This refactor does not make the anomaly model compatible with Python 3.11/Apple Silicon. It only gives it a clear home and honest run documentation.
- Moving generated `output/` artifacts preserves the current demo state but continues to keep large generated files in the repository until a later cleanup decision.
- Existing imports are flat module imports. Keeping execution from `backend/` avoids a broader Python packaging conversion.
- The currently running Flask process uses the pre-move module location and must be stopped before files move, then restarted from `backend/`.

## Assumptions

- `Website/` is the standalone frontend and should remain outside `backend/`.
- `data.csv` and the annotation dataset are reference/research data because active backend code does not load them.
- The desired outcome is organization and run documentation, not ML modernization.
- Safe local mode should remain the only mode run during this task.
- No Git commit, branch, or push is requested.

## Review decision

Implementation is approved using the recommended scope: `data.csv` and `Temporal_Anomaly_Annotation_For_Testing_Videos/` will remain root-level research artifacts because active backend runtime code does not read them.

## Implementation todo list

### Phase 1: Prepare the repository structure

- [x] Stop the currently running root-level Flask development server.
- [x] Create the `backend/` directory.
- [x] Move Flask backend modules into `backend/`.
- [x] Move anomaly-detection modules and `utils/` into `backend/`.
- [x] Move `templates/`, `static/`, `trained_models/`, `input/`, and `output/` into `backend/`.
- [x] Leave `Website/`, `Website.zip`, `data.csv`, and the annotation dataset at the repository root.
- [x] Remove generated root-level Python cache files and update `.gitignore` for cache directories and the new model-weight location.

### Phase 2: Make the moved backend self-contained

- [x] Add the police, hospital, and fire icons to `backend/static/images/` without removing the standalone frontend copies.
- [x] Update `backend/templates/test.html` to load all icons from Flask static assets.
- [x] Remove the cross-boundary `Website/` asset route and unused `send_from_directory` import from `backend/app.py`.
- [x] Verify configuration paths still resolve from the `backend/` working directory.
- [x] Verify Python module imports resolve entirely within `backend/`.

### Phase 3: Add dependency and run documentation

- [x] Add `backend/requirements-web.txt` for safe local Flask mode.
- [x] Add `backend/README.md` covering safe local mode, opt-in live Firebase mode, and the limitations of the legacy anomaly demo.
- [x] Replace the root README with a repository map and a link to the backend instructions.
- [x] Update `research.md` to reflect the new paths and project boundary.

### Phase 4: Validate the refactor

- [x] Compile all backend Python source files from `backend/`.
- [x] Import the Flask application and inspect its URL map.
- [x] Run Flask test-client checks for `/`, `POST /test`, CSS, JavaScript behavior, and all three icons.
- [x] Confirm safe local mode does not import missing ML/Firebase packages or perform remote operations.
- [x] Start the Flask server from `backend/` and verify `/` and `/test` over HTTP.
- [x] Confirm the root no longer contains backend/anomaly runtime files.
- [x] Run whitespace/error checks on changed text files.
- [x] Mark every completed todo in this plan.

## Themed analysis GIF plan (October 2026)

> I want to build a new feature `Vigil-themed analysis GIF` that extends the system to produce a polished video-classification visualization consistent with the Demo/Test website.

### Feature summary and outcome

Replace the generic square Matplotlib animation with a landscape Vigil analysis card. The generated `out.gif` should feel native to the black-green product UI while showing the monitored video and detected moments on the left, plus the evolving anomaly signal, live score, and playback progress on the right.

### Current state

`demo.py` calls `visualize_predictions()` after inference. The renderer currently creates a 600 × 600 default Matplotlib figure, divides it into two equal axis-heavy panels, samples every tenth frame, and saves at 10 FPS. The frontend and API treat `out.gif` as an opaque artifact, so their contracts do not need to change.

### Proposed technical approach

1. Define module-level Vigil visualization colors and a small figure-construction helper in `utils/visualization_util.py`.
2. Build a moderate-resolution 16:9 canvas with a left video column and right signal panel.
3. Remove standard video axes and style chart spines, ticks, grid, typography, and backgrounds with the same tokens used by the website.
4. Add the surfaced anomaly frames as a stable thumbnail strip directly below the video, highlighting the detected moment nearest the current animation frame.
5. Draw the full prediction trace in a subdued color, reveal the observed portion in bright green, shade the observed signal, and add a moving current-score marker.
6. Add a visible threshold guide and dynamically update frame progress, score text, and signal status.
7. Preserve the current frame sampling, GIF filename, 10 FPS playback, extracted-frame logic, and returned anomaly indices.

### Files to modify

- `backend/utils/visualization_util.py`: themed layout and animation artists.
- `backend/tests/test_visualization_util.py`: focused style/layout and small-GIF tests.
- `backend/README.md`: describe the themed visualization and regeneration command.
- `research.md` and `plan.md`: record implementation and validation results.

No API, database, model, schema, JavaScript, or CSS changes are required.

### Important implementation shape

```python
figure, artists = build_analysis_figure(frames[0], predictions)

def update(frame_index):
    artists.frame_image.set_data(frames[frame_index])
    artists.score_line.set_data(x[:frame_index + 1], predictions[:frame_index + 1])
    artists.marker.set_data([frame_index], [predictions[frame_index]])
    artists.score_text.set_text(f"{predictions[frame_index]:.3f}")
    artists.progress_text.set_text(f"FRAME {frame_index + 1:04d} / {len(frames):04d}")
    return artists.dynamic
```

The actual implementation should use a simple established Python structure rather than introduce a broad visualization framework.

### Feedback decision

The user selected the revised mock layout: the video occupies the upper-left area, detected frames form a row below it, and the complete graph panel stays on the right. If the existing anomaly heuristic surfaces fewer than five moments, the thumbnail strip will display a restrained `No detected moments` state instead of inventing frames.

### Error handling and validation

- Retain the existing frame/prediction length error.
- Keep output-directory creation and stale extracted-frame cleanup unchanged.
- Ensure figures close even if GIF writing raises, preventing Matplotlib resource leaks.
- Validate empty prediction input directly if needed by the layout helper.
- Avoid accumulating fill or text artists on animation updates.

### Test and manual verification strategy

1. Run Python compilation and `pip check` in `backend/vigil_env`.
2. Add a focused layout test that verifies canvas aspect, dark surfaces, green signal styling, threshold guide, and initial labels.
3. Generate a tiny GIF from synthetic frames/predictions and verify it is readable, landscape, animated, and returns the expected anomaly indexes.
4. Run the full pytest suite.
5. Run `git diff --check`.
6. After implementation, regenerate the included `out.gif` with the documented CLI and visually inspect a representative frame only if the user approves the inference run; do not start the web server.

### Risks and tradeoffs

- A landscape canvas may create a larger GIF; moderate dimensions and existing temporal sampling control size.
- GIF color quantization limits subtle effects, so the design favors crisp hierarchy over complex gradients.
- A fixed threshold is presentation context, not a change to classifier behavior or the existing anomaly extraction heuristic.
- Full sample regeneration runs the expensive classifier and should remain a separate explicit validation step.

### Assumptions

- Matching the UI means reusing its palette, typography hierarchy, minimal borders, and neon signal treatment rather than reproducing browser-only effects exactly.
- `out.gif` remains the output contract and should work in both Demo and Test without frontend changes.
- The classification model, prediction values, and surfaced-frame selection must not change.

### Implementation todo list

#### Phase 1: Themed layout foundation

- [x] Add shared Vigil visualization color constants.
- [x] Add a focused analysis-figure builder with a 16:9 dark canvas.
- [x] Build the left video stage and right signal panel without default Matplotlib chrome.
- [x] Add branded header, feed state, frame progress, model label, and timeline progress.

#### Phase 2: Detected moments and animated signal

- [x] Render surfaced anomaly frames in a strip directly below the video.
- [x] Add a clear empty state when the existing heuristic produces fewer than five surfaced moments.
- [x] Highlight the detected thumbnail nearest the current animation frame.
- [x] Style the full signal context, observed trace, fill, threshold, and moving marker.
- [x] Update score, status, progress, and video artists without accumulating artists per frame.
- [x] Preserve frame sampling, playback speed, extracted PNGs, filenames, and returned anomaly indexes.

#### Phase 3: Reliability and tests

- [x] Ensure the Matplotlib figure closes on both successful and failed GIF writes.
- [x] Add a focused layout/style test for dimensions, colors, labels, threshold, and thumbnail placement.
- [x] Add a small synthetic animation test for readable landscape GIF output and anomaly-index behavior.
- [x] Run Python compilation, `pip check`, JavaScript syntax validation, and the complete pytest suite.
- [x] Run `git diff --check`.

#### Phase 4: Documentation and visual verification

- [x] Update the README output description and regeneration command.
- [x] Record final implementation facts and validation results in `research.md`.
- [x] Regenerate the included sample GIF only if explicitly approved; do not start the web server.
- [x] Inspect representative output frames for video, thumbnails, graph, labels, and GIF palette quality.
- [x] Mark every completed task in this feature plan.

## Reference-driven dashboard UI plan (October 2026)

> I want to build a new feature `reference-driven Vigil dashboard UI` that extends the system to present its existing Demo and Test workflows in the compact video-anomaly product experience shown in the supplied dashboard image.

### Feature summary and business outcome

Redesign the local Vigil website around the supplied `Vigil_ Video Anomaly Intelligence Dashboard.png`. The result should feel like one coherent security-analysis product: a compact conversion-focused hero followed by a dense dashboard workspace for sample analysis and local video upload. Existing capabilities remain intact and no unavailable incident-management features will be fabricated.

### Current-state summary

The current application has a large editorial hero, decorative method section, floating Demo/Test pill, upload form, shared result viewer, and responsive CSS. Its APIs and JavaScript state model already support everything needed. The primary gap is visual structure: page sections are oversized, navigation is detached from the dashboard, and the result area does not use the compact sidebar/content framing of the new reference.

### Proposed technical approach

1. Replace the current decorative landing content with a compact reference-matched hero: short top bar, local CPU badge, centered eyebrow/headline/copy, two CTAs, a privacy reassurance line, and restrained curved signal decoration.
2. Convert Demo/Test navigation into an application sidebar on desktop. Use `Analyze` for Test and `Sample analysis` for Demo so labels describe actual capabilities.
3. Place the tab panels inside a dashboard content region with compact titles and card spacing.
4. Restyle the upload experience into the reference's two-card pattern: drop zone beside selected-video/action details on wide screens, with a single-column fallback before selection or on small screens.
5. Restyle the shared result viewer into a media-and-details dashboard: analysis preview in the main column, factual run metrics in a right rail, and detected frames below the preview.
6. Add hero CTA behavior using the existing tab activation path. `Analyze footage` activates Test; `View sample analysis` activates Demo; both scroll to the dashboard.
7. Preserve the API payload, upload behavior, current frame interactions, keyboard tab navigation, ARIA, focus states, reduced motion, and local-processing copy.

### Files and modules

- `backend/templates/home.html`: new semantic hero, dashboard sidebar, compact Demo/Test panels, and revised result template.
- `backend/static/css/styles.css`: complete reference-driven visual layout and responsive rules.
- `backend/static/js/app.js`: CTA hooks and selectors required by the revised structure; reuse all upload/result logic.
- `backend/tests/test_web_app.py`: assert the new dashboard structure and continued absence of legacy dependencies.
- `backend/README.md`: no workflow change expected; update only if visible navigation terminology needs explanation.
- `research.md` and `plan.md`: implementation facts and validation status.

### UI and state mapping

| Reference concept | Vigil implementation |
|---|---|
| Analyze | Test tab and upload form |
| Incidents/sample evidence | Demo tab and generated output |
| Video/chart workspace | Generated `out.gif` |
| Incident details | Factual run summary metrics |
| Evidence frames | Surfaced moment thumbnails |
| Local CPU badge | Existing model-status indicator |

Incidents CRUD, severity, semantic labels, confirmation actions, false-positive actions, and evaluation history remain out of scope because there is no supporting model or persistence layer.

### Interaction outline

```javascript
heroAnalyze.addEventListener("click", () => activateTab("test"));
heroDemo.addEventListener("click", () => activateTab("demo"));

function activateTab(name, focus = false, shouldScroll = true) {
  // Preserve ARIA/tabindex updates and toggle the revised dashboard panels.
}
```

The existing shared `renderResult()` continues to populate the GIF, metrics, and frame buttons. Markup class names can change, but the returned JSON contract does not.

### Error handling and validation

- Preserve all current upload type, size, and empty-file checks.
- Preserve empty-demo, busy, processing, server-error, and retry states.
- Ensure selected-file details do not overflow compact cards.
- Ensure CTA and sidebar controls remain usable without a mouse.
- Keep truthful labels: surfaced moments are anomaly-score transitions, not classified incidents.

### Test and manual verification strategy

1. Run `node --check` after JavaScript changes.
2. Run Python compilation, `pip check`, and the complete pytest suite.
3. Extend HTML tests for the hero CTAs, dashboard shell, sidebar tab controls, upload form, and result template.
4. Render desktop and mobile screenshots without starting a persistent server, then compare hierarchy, spacing, palette, and density against the supplied image.
5. Exercise both CTAs, sidebar keyboard navigation, file selection/removal, Demo loading, detected-frame selection, GIF restoration, and reduced-motion behavior.
6. Run `git diff --check` and confirm no Firebase, Bootstrap, Plotly, or fake incident-action code entered the active UI.

### Risks and tradeoffs

- The reference is a composite mockup rather than a single production screen, so the page must synthesize its hero and application views into one scrollable local demo.
- A dense desktop dashboard can become cramped on mobile; responsive layout must prioritize content order over exact geometry.
- The updated GIF already includes detected frames and a graph. The webpage will retain selectable thumbnails and metrics because they provide interaction and accessible details, but avoid introducing a second synthetic chart.
- A CSS rewrite is lower risk than changing the API or result schema and keeps this redesign focused.

### Assumptions

- The reference image governs the new visual direction and supersedes the earlier DOTDNA landing-page framing.
- Both the hero and dashboard workspace should remain on the same page.
- `Demo` and `Test` behavior remains unchanged even if visible navigation labels become `Sample analysis` and `Analyze`.
- The current black-green palette, Vigil identity, and local-only positioning remain correct.
- No backend or model changes are requested.

---

# Minimal Vigil Demo Website Plan (superseded)

> I want to build a new feature `a minimal, premium Vigil demo website inspired by Ambient.ai's physical-security storytelling and the Fort Sec visual system` that extends the system to perform `a clear, credible showcase of the anomaly detector using the generated output folder`.

## Feature summary and business outcome

Replace the legacy form/Firebase dashboard as the primary Flask experience with one polished, responsive demo page. The page will explain Vigil in a few sentences, present the real generated anomaly output, let a viewer inspect the six surfaced frames, and explain the three-step detection flow.

The proposed default is a read-only product demo. It will not upload videos or run the 80-million-parameter model inside a web request. This keeps the demonstration fast, deterministic, safe, and honest while showcasing the actual working pipeline.

## Current-state summary

- The ML pipeline successfully produces `out.gif`, `predictions.npy`, and six `fr*.png` incident frames in `backend/output/`.
- The current root route is an unstyled Submit form.
- The current `/test` page is a 3.4 MB legacy artifact with embedded Plotly, Firebase coupling, unrelated map data, and emergency-service controls.
- The existing stylesheet is Bootstrap-oriented and does not support the requested visual direction.
- Flask does not currently expose generated output through an explicit, tested route.

## Proposed experience

### Header

- Compact `Vigil` wordmark with a small geometric shield/eye mark made in CSS or inline SVG.
- Two in-page links: `How it works` and `Detection demo`.
- A restrained status pill: `Local AI demo`.

### Hero

- Editorial headline: **See the moment that matters.**
- Supporting copy: Vigil turns surveillance footage into frame-level anomaly signals, helping security teams focus on meaningful activity.
- Primary CTA: `View detection` scrolling to the real output.
- Small proof line using only verified facts: `1,159 frames · 72 clips · 6 surfaced moments`.
- Dark near-black field with subtle violet/blue atmospheric gradients and a fine technical grid.

### Detection demo

- Large bordered media card showing `output/out.gif`.
- Play/pause control that swaps the animated GIF with `fr0.png` to respect user control and reduced-motion preferences.
- A compact run header with `Completed`, duration, frame count, and max anomaly score.
- Six incident thumbnails sourced from `fr0.png`–`fr5.png`.
- Clicking a thumbnail switches the focal media to that frame and updates the incident label.
- `View analysis` restores the animated GIF.
- Clear caption that these are score-transition frames, not semantic incident classifications.

### How it works

Three minimal cards:

1. `01 / Monitor` — decode footage into 16-frame clips.
2. `02 / Score` — extract C3D features and produce frame-level anomaly scores.
3. `03 / Surface` — elevate rapid score changes for operator review.

### Footer

- Vigil wordmark.
- `Local research demo — outputs are pre-generated.`
- No contact form or fake commercial links.

## Visual system

- Canvas: `#050506` and slightly lifted card surfaces.
- Primary text: cool near-white; secondary text: `#B2B5C4`.
- Accent: restrained `#7688C1`, `#8F57BE`, and electric violet gradients.
- Display typography: local editorial serif stack (`Iowan Old Style`, `Baskerville`, `Times New Roman`) to avoid a runtime font dependency.
- Interface typography: system sans-serif stack.
- Hairline borders, 18–24px card radii, generous whitespace, and minimal glow.
- No copied Fort Sec illustrations, logos, layout text, or decorative assets.

## Proposed technical approach

### 1. Generate web-readable demo metadata

Extend `demo.py` to write `output/summary.json` after successful inference:

```json
{
  "frame_count": 1159,
  "complete_clips": 72,
  "fps": 30.0,
  "duration_seconds": 38.63,
  "score_min": 0.00000153,
  "score_max": 0.99999970,
  "surfaced_frames": [179, 195, 211, 227, 243, 259]
}
```

The exact surfaced frame indexes will come from the completed run rather than the illustrative values above. The current output will receive a matching summary during implementation.

### 2. Simplify Flask around a read-only demo

`app.py` will:

- Load `output/summary.json` with the standard `json` module.
- Discover and naturally sort `fr*.png` files.
- Render `/` with a small demo view model.
- Serve generated files through `GET /output/<path:filename>` using `send_from_directory`.
- Restrict output serving to the configured output directory through Flask's safe path resolution.
- Render an empty state when output files are missing.

The primary app will no longer import Requests or maintain Firebase notification logic. That legacy integration remains in source history/research but is outside the minimal demo requirement.

Representative view model:

```python
demo = {
    "ready": gif_path.is_file() and summary_path.is_file(),
    "gif_url": url_for("output_file", filename="out.gif"),
    "frames": [...],
    "summary": summary,
}
```

### 3. Build the page without a frontend framework

- Replace `templates/home.html` with semantic HTML and Jinja rendering.
- Replace `static/css/styles.css` with a custom responsive stylesheet.
- Add `static/js/demo.js` using small DOM event handlers only.
- Do not load Bootstrap, Firebase JS, Plotly, or a JavaScript package manager.
- Use an inline SVG/CSS brand mark and CSS-generated atmosphere to avoid new image assets.

### 4. Remove legacy primary-page baggage

- Remove the `/test` form flow and Firebase action controls from `app.py`.
- Remove `templates/test.html`, whose embedded Plotly bundle accounts for most of the legacy frontend weight.
- Remove `static/images/firebase.js` if no remaining route uses it.
- Keep the police/fire/hospital icons only if another retained surface still references them; otherwise remove them from Flask static assets.

These deletions are scoped to the Flask demo frontend. They do not affect ML inference or the root-level standalone `Website/` archive.

## Files and modules to create, modify, or remove

### Create

- `backend/static/js/demo.js`.
- `backend/output/summary.json` (generated artifact, ignored by Git if output artifacts remain generated).
- Focused Flask/demo metadata tests.

### Modify

- `backend/app.py`.
- `backend/demo.py`.
- `backend/templates/home.html`.
- `backend/static/css/styles.css`.
- `backend/README.md`.
- `.gitignore` if `summary.json` should remain generated-only.
- `research.md` and `plan.md`.

### Remove from the Flask surface

- `backend/templates/test.html`.
- `backend/static/images/firebase.js`.
- Unused emergency-service icon files if no retained template references them.

## Data, API, UI, and integration changes

- `/` becomes the complete demo instead of a trigger form.
- `/test` is removed.
- `/output/<filename>` is added for generated demo artifacts.
- Inference adds `summary.json`; model behavior and predictions remain unchanged.
- Firebase notification and dashboard writes are removed from the demo web process.
- No database, authentication, upload, or background-job system is introduced.

## Error handling and empty states

- Missing `summary.json` or `out.gif`: show a styled empty state with the exact local inference command.
- Missing individual frames: omit those thumbnails without breaking the page.
- Invalid JSON: treat the demo as unavailable and log the parsing error during development/testing.
- Missing JavaScript: the GIF and frame links remain visible; JS only enhances switching behavior.
- Broken output request: return Flask's standard 404.

## Validation strategy

### Automated

- Python compile check.
- Existing ML test suite.
- Flask test-client checks for `/`, generated GIF, each frame, CSS, and JS.
- Empty-output fixture test.
- Summary JSON generation test using mocked inference results or a small direct helper.
- Assert rendered HTML contains no Bootstrap, Firebase, or Plotly dependencies.
- Assert unsafe output traversal returns 404.

### Manual and visual

- Render the page locally at desktop and mobile widths.
- Verify visual hierarchy against the Fort Sec traits without copying its artwork.
- Verify GIF play/pause, frame selection, restore-analysis control, anchor navigation, keyboard focus, and reduced-motion behavior.
- Confirm no Firebase/network requests occur during page use.
- Confirm all copy reflects verified project capabilities.

## Risks and tradeoffs

- Animated GIF playback is less controllable than video; the still/GIF swap provides a practical minimal control.
- The output is a square visualization rather than cinematic surveillance footage, so the design must frame it as analysis evidence rather than stretch it into a hero background.
- Removing the legacy `/test` route drops live Firebase controls from the primary Flask app. This is consistent with the minimal local demo but requires confirmation if those controls must remain accessible.
- A read-only demo cannot accept arbitrary visitor footage. Browser-triggered inference would require upload security, job orchestration, timeouts, storage cleanup, and a substantially larger scope.
- The generated metadata can become stale if output files are manually replaced; writing it atomically during inference keeps normal runs consistent.

## Assumptions

- The visible brand name is `Vigil`.
- The website is a local/read-only demonstration of the already-generated output.
- The current output folder is representative and can be shown publicly in the local demo.
- Existing Firebase controls are not required in the new minimal experience.
- No new AI-generated artwork is necessary; the real output and CSS atmosphere are stronger evidence.
- No Git commit, branch, deployment, or public publishing is requested.

## Questions for review

1. Should the demo remain read-only with the pre-generated output (recommended), or must visitors upload a video and run inference from the website?
2. Is `Vigil` the correct visible product name, and may the legacy `/test` Firebase dashboard be removed from the Flask app?

The user resolved these questions and corrected the design reference. The plan above is superseded. The implementation must use the revised plan below.

---

# Revised Vigil Demo and Test Website Plan

> I want to build a new feature `a DOTDNA-inspired Vigil website with Demo and Test tabs` that extends the system to perform `both a polished showcase of pre-generated anomaly results and local user-uploaded video analysis without Firebase`.

## Feature summary and business outcome

Build one minimal local web application under the `Vigil` name. `Demo` presents the known-good generated output immediately. `Test` accepts a video, runs the existing model locally, and presents the result using the same viewer.

The design will follow the corrected DOTDNA reference: deep black-green environment, large rounded application frame, oversized centered sans-serif typography, acid-green accents, sparse particles, thin perspective lines, low-contrast supporting content, and floating pill navigation.

## Confirmed decisions

- Product name: `Vigil`.
- Primary modes: `Demo` and `Test`.
- Demo source: pre-generated files in `backend/output/`.
- Test behavior: upload a video and run real local backend inference.
- Legacy Bootstrap, Plotly, Firebase, emergency-service UI, and `/test` route: remove.
- Visual reference: DOTDNA, not Fort Sec.
- Existing inference model and anomaly heuristic: preserve.

## User experience

### Application frame

- Full viewport dark-green atmosphere with faint radial illumination and CSS particles.
- One large near-black rounded frame with subtle green border.
- Top-left Vigil mark/wordmark.
- Top-right compact model status: `C3D · Local CPU` with a green status dot.
- Bottom-centered floating pill tabs: `Demo` and `Test`.

### Intro state

- Large centered headline: **See what changed. Before it escalates.**
- Concise explanation that Vigil scores surveillance footage and surfaces rapid anomaly transitions for review.
- Abstract point-cluster motif built with CSS/SVG dots, not copied imagery.
- Three quiet proof statements across the lower field:
  - `01 / Monitor` — 16-frame temporal clips.
  - `02 / Score` — frame-level anomaly signal.
  - `03 / Surface` — reviewable moments.

### Demo tab

- Uses `backend/output/summary.json`, `out.gif`, and `fr*.png`.
- Shows the analysis GIF as the primary preview.
- Displays verified run metadata: duration, frame count, clip count, surfaced moments, and score range.
- Shows surfaced-frame thumbnails.
- Clicking a thumbnail replaces the main preview; `View full analysis` restores the GIF.
- Includes a short disclaimer: surfaced frames represent score changes, not semantic incident labels.

### Test tab

- Drag-and-drop/file picker accepting MP4, MOV, AVI, and MKV up to 100 MB.
- Selected-file state with name and human-readable size.
- Explicit `Analyze video` button.
- Processing state with spinner/particle pulse, elapsed time, and truthful copy that local CPU analysis may take about as long as the sample run.
- Success state reuses the Demo result viewer with the uploaded run's artifacts.
- Failure state displays a useful server-provided message and retry control.

## Backend design

### Application routes

```text
GET  /                         -> two-tab application shell
GET  /api/demo                 -> pre-generated demo result JSON
POST /api/analyze              -> validate upload, run inference, return result JSON
GET  /output/<path:filename>   -> serve generated artifacts safely
```

### Result metadata

Extend `run_demo()` to return and atomically write:

```json
{
  "frame_count": 1159,
  "complete_clips": 72,
  "fps": 30.0,
  "duration_seconds": 38.633,
  "score_min": 0.00000153,
  "score_max": 0.99999970,
  "surfaced_frame_indices": ["actual indexes from inference"],
  "surfaced_frame_files": ["fr0.png", "fr1.png"],
  "analysis_file": "out.gif"
}
```

Use a temporary file plus `replace()` so the website never reads a partially written summary.

### Cached inference service

Add a small service layer in `app.py` or a focused `inference_service.py`:

- Lazy-load `c3d_feature_extractor()` and `build_classifier_model()` on the first Test request.
- Cache both models for subsequent requests.
- Guard load/inference with one `threading.Lock`.
- Pass cached models into `run_demo()` rather than rebuilding them.
- Never import TensorFlow during a Demo-only page request.

Representative shape:

```python
class InferenceService:
    def analyze(self, video_path, output_dir):
        with self._lock:
            models = self._get_models()
            return run_demo(video_path, output_dir, models=models)
```

### Upload handling

- Configure `MAX_CONTENT_LENGTH = 100 * 1024 * 1024`.
- Require multipart field `video`.
- Validate extension case-insensitively.
- Generate a UUID job ID; never use the client filename as a filesystem path.
- Save to a temporary directory under `backend/runtime/uploads/<job-id>/`.
- Write outputs to `backend/output/runs/<job-id>/`.
- Remove the uploaded source and temporary directory in `finally`.
- Keep generated result artifacts for the local session.
- Reject concurrent Test inference with HTTP `409` and a clear message rather than queueing silently.
- Return JSON errors with appropriate `400`, `409`, `413`, or `500` status.

### Result serialization

One helper converts a summary directory into the same JSON schema for both Demo and Test:

```python
{
    "ready": True,
    "summary": summary,
    "analysis_url": url_for("output_file", filename=relative_gif),
    "frames": [{"label": "Moment 01", "url": ...}],
}
```

## Frontend implementation

### HTML

- Replace `home.html` with one semantic shell containing intro, Demo, and Test panels.
- Render only stable initial markup from Jinja.
- Use `aria-selected`, tab roles, labelled upload input, live status region, and keyboard-operable controls.
- Use a `<noscript>` demo fallback.

### CSS

Use the corrected DOTDNA relationships:

- Background `#010301`.
- Frame/card black-green close to `#020602`.
- Primary text `#DFFCE8`.
- Secondary text `#778676`/`#A4C1AA`.
- Border/quiet structure `#364A32` and `#5B6559` at low opacity.
- Accent `#25B103`.
- Modern system sans-serif throughout; no editorial serif.
- 32–48px application radius on desktop, reduced on mobile.
- CSS-generated perspective lines, glow, grain, and dots.

### JavaScript

Add one dependency-free `static/js/app.js` to:

- Switch Demo/Test tabs and synchronize ARIA state.
- Fetch `/api/demo` once and render the viewer.
- Handle drag/drop and file selection.
- Validate client-side extension and size before upload.
- Submit multipart upload to `/api/analyze`.
- Track elapsed processing time.
- Render success/errors safely using DOM APIs rather than HTML injection.
- Switch between GIF and surfaced-frame previews.

## Files to create, modify, and remove

### Create

- `backend/inference_service.py`.
- `backend/static/js/app.js`.
- `backend/tests/test_web_app.py`.
- `backend/output/summary.json` for the current pre-generated run.
- Runtime directories as needed; ignored by Git.

### Modify

- `backend/app.py`.
- `backend/demo.py`.
- `backend/templates/home.html`.
- `backend/static/css/styles.css`.
- `backend/README.md`.
- `.gitignore`.
- `research.md` and `plan.md`.

### Remove

- `backend/templates/test.html`.
- `backend/static/images/firebase.js`.
- `backend/static/images/police.png`.
- `backend/static/images/hospital.png`.
- `backend/static/images/fire.png`.

The root-level `Website/` archive remains untouched unless separately requested.

## Error handling

- Missing demo artifacts: `/api/demo` returns `ready: false`; UI displays the exact CLI command to generate them.
- Unsupported or empty upload: HTTP `400`.
- Upload larger than 100 MB: HTTP `413` JSON response.
- Another inference in progress: HTTP `409`.
- Video cannot be decoded or is shorter than 16 frames: HTTP `400` with the validated model error.
- Unexpected model/GIF failure: HTTP `500`, logged server-side, generic actionable UI message.
- Temporary upload cleanup runs for both success and failure.
- Result serving outside `backend/output/`: Flask safe path handling returns `404`.

## Automated validation

- Preserve all nine existing ML tests.
- Test summary generation and atomic write.
- Test `/`, `/api/demo`, and output artifact routes.
- Test missing-demo empty state.
- Test accepted extensions and case handling.
- Test missing, empty, unsupported, and oversized uploads.
- Mock inference for successful API result and model failure.
- Test `409` busy response.
- Test upload cleanup after success/failure.
- Test output traversal rejection.
- Assert rendered HTML has no Bootstrap, Plotly, Firebase, or legacy `/test` dependencies.
- Compile Python and run `git diff --check`.

## Manual validation

- Run one real Test upload using the included video and verify isolated artifacts.
- Compare Test result metadata to the known CLI inference behavior.
- Check desktop and mobile layouts.
- Verify keyboard tab operation, focus styles, live processing status, drag/drop, retry, frame switching, and GIF restoration.
- Confirm Demo browsing does not import/load TensorFlow.
- Confirm no Firebase requests occur.

## Risks and tradeoffs

- Synchronous local inference keeps implementation minimal but holds one HTTP request for roughly a minute. It is appropriate for a single-user local demo, not production hosting.
- Caching models increases Flask process memory after the first Test request but dramatically reduces later startup overhead.
- Keeping per-run output folders can consume disk over time; a local manual cleanup instruction will be documented. Automatic destructive cleanup is intentionally excluded.
- Browser support for container/codec combinations varies, but analysis uses server-side OpenCV and result viewing uses generated GIF/PNG files.
- Visual particles and lines must remain subtle so real model output—not decoration—stays primary.

## Assumptions

- One local user at a time.
- 100 MB is an acceptable upload limit.
- Synchronous processing with elapsed-time feedback is acceptable for the demo.
- Uploaded source videos should be deleted after inference; generated results may remain locally.
- No authentication or public deployment is required.
- No Firebase, database, background queue, or cloud storage is required.
- No Git commit, branch, or push is requested.

## Implementation todo list

### Phase 1: Result metadata and inference reuse

- [x] Add a summary builder that records video metadata, score range, clip count, surfaced frame indexes/files, and analysis filename.
- [x] Write `summary.json` atomically after successful inference.
- [x] Update `run_demo()` to accept optional preloaded feature-extractor and classifier models.
- [x] Return structured summary data from `run_demo()` without changing CLI behavior.
- [x] Generate `backend/output/summary.json` for the existing pre-generated demo.
- [x] Add focused tests for summary contents and atomic writing.

### Phase 2: Cached local inference service

- [x] Create `backend/inference_service.py`.
- [x] Lazy-load and cache both TensorFlow/Keras models.
- [x] Serialize model loading and inference with a process-local lock.
- [x] Expose a non-blocking busy check so concurrent requests receive HTTP `409`.
- [x] Pass cached models into `run_demo()`.
- [x] Ensure uploaded source cleanup runs after both success and failure.
- [x] Add isolated tests for caching, busy behavior, and cleanup.

### Phase 3: Minimal Flask API

- [x] Replace legacy `app.py` Firebase behavior with the Demo/Test web application.
- [x] Configure the 100 MB request limit.
- [x] Add `GET /api/demo`.
- [x] Add `POST /api/analyze` with multipart validation.
- [x] Accept MP4, MOV, AVI, and MKV extensions case-insensitively.
- [x] Use UUID job paths and never trust the client filename as a path.
- [x] Store generated results under `output/runs/<job-id>/`.
- [x] Add safe `GET /output/<path:filename>` artifact serving.
- [x] Return consistent JSON errors for `400`, `409`, `413`, and `500` cases.
- [x] Ensure Demo-only requests do not import or initialize TensorFlow.

### Phase 4: DOTDNA-inspired application UI

- [x] Replace `templates/home.html` with the semantic two-tab application shell.
- [x] Replace the legacy stylesheet with the black-green/neon Vigil design system.
- [x] Add CSS-generated particles, perspective lines, glow, grain, and responsive framing.
- [x] Add accessible Demo/Test floating pill navigation.
- [x] Build a shared result viewer for the analysis GIF, metadata, and surfaced frames.
- [x] Build the Test drag/drop, file selection, validation, and Analyze states.
- [x] Add processing elapsed-time feedback and honest local-CPU messaging.
- [x] Add success, empty-demo, error, busy, and retry states.
- [x] Add dependency-free `static/js/app.js` for tabs, upload, rendering, and preview switching.
- [x] Preserve keyboard support, visible focus, ARIA state, and reduced-motion behavior.

### Phase 5: Remove legacy Flask UI

- [x] Remove `templates/test.html`.
- [x] Remove Firebase browser JavaScript.
- [x] Remove unused emergency-service icons from Flask static assets.
- [x] Confirm Bootstrap, Plotly, Firebase, and `/test` are absent from the active Flask surface.
- [x] Leave the root-level `Website/` archive untouched.

### Phase 6: Automated validation

- [x] Add Flask tests for `/`, `/api/demo`, and generated artifact serving.
- [x] Test missing-demo behavior.
- [x] Test missing, empty, unsupported, and accepted upload inputs.
- [x] Test case-insensitive file extensions.
- [x] Test mocked successful inference response.
- [x] Test model/processing failure response and upload cleanup.
- [x] Test HTTP `409` while inference is busy.
- [x] Test HTTP `413` for oversized requests.
- [x] Test path traversal rejection.
- [x] Assert active HTML excludes Bootstrap, Plotly, Firebase, and legacy routes.
- [x] Run Python compilation and the full test suite continuously.

### Phase 7: Real inference and visual verification

- [x] Run a real Test upload using the included sample video.
- [x] Verify isolated output artifacts and summary metadata.
- [x] Verify the pre-generated Demo API and Test result use the same schema.
- [x] Start the local Flask server and verify all HTTP endpoints.
- [x] Render the page at desktop width and inspect visual fidelity to the DOTDNA reference.
- [x] Render the page at mobile width and verify responsive behavior.
- [x] Verify Demo/Test tabs, upload selection, processing state, frame selection, and GIF restoration.
- [x] Verify keyboard focus, ARIA tab state, and reduced-motion behavior.
- [x] Confirm no Firebase requests or TensorFlow load occurs during Demo-only use.

### Phase 8: Documentation and completion

- [x] Update `backend/README.md` with Demo/Test setup, upload constraints, runtime expectations, result paths, and cleanup guidance.
- [x] Update `.gitignore` for temporary uploads and generated run folders.
- [x] Update `research.md` with final implementation facts and validation results.
- [x] Run dependency, whitespace, and repository status checks.
- [x] Mark every completed todo in this plan.

---

# Local ML Runtime Modernization Plan

> I want to build a new feature `a modern local anomaly-detection runtime` that extends the system to perform `end-to-end video anomaly inference on the user's Apple Silicon Mac with Python 3.11, without requiring live Firebase access`.

## Feature summary and business outcome

Port the checked-in C3D anomaly-detection pipeline from its 2018 TensorFlow 1/Keras 2 stack to the officially supported modern TensorFlow CPU stack for macOS ARM64. A developer should be able to create one virtual environment, install declared dependencies, download the documented public C3D weights, run the included video locally, and receive a GIF, anomaly scores, and extracted frames without contacting Firebase.

Firebase upload will remain available only as an explicit optional action. The existing safe local Flask app must continue working.

## Current-state summary

- The target is macOS 15.1.1, Apple Silicon, Python 3.11.3.
- Official TensorFlow documentation provides a current macOS ARM64/Python 3.11 CPU wheel.
- The code uses removed APIs: `scipy.misc.imresize`, old Keras import modules, and legacy model construction conventions.
- `demo.py` imports Pyrebase unconditionally and uploads every completed run to the configured Firebase project.
- The classifier MATLAB weights are present and structurally match the code.
- The required public C3D Sports-1M weights are absent; the valid download is 320,010,428 bytes.
- There is no golden output or automated ML test suite.

## Proposed technical approach

### 1. Create an isolated modern ML environment

Add `backend/requirements-ml.txt` with compatible, tested versions for:

- TensorFlow CPU on macOS ARM64.
- NumPy and SciPy.
- OpenCV.
- Matplotlib and Pillow.
- HDF5 support.
- Existing web requirements so one ML environment can also run Flask.

Create `backend/vigil_env` and install this manifest. The virtual environment remains ignored by Git.

### 2. Acquire and verify the public model artifact

Download the documented C3D weights into:

```text
backend/trained_models/c3d_sports1m.h5
```

Record the downloaded file's SHA-256 checksum in the backend README. Keep the file ignored by Git. The code will never silently download this 320 MB model during normal inference; setup instructions will make the large download explicit.

The smaller C3D mean array may continue using the official Keras cache helper with its existing MD5 verification, or may be downloaded into the project model directory if cache-directory permissions make that more reliable during implementation.

### 3. Port the C3D and classifier models

Update `backend/c3d.py` to:

- Use modern TensorFlow/Keras imports consistently.
- Replace SciPy resize with OpenCV bicubic resize.
- Use an explicit input tensor.
- Preserve all layer names, order, shapes, activations, padding, and dropout positions so legacy topological HDF5 weights can load.
- Return the `fc6` feature extractor exactly as before.

Representative structure:

```python
from tensorflow import keras

model = keras.Sequential([
    keras.Input(shape=(16, 112, 112, 3)),
    keras.layers.Conv3D(64, 3, activation="relu", padding="same", name="conv1"),
    # Existing layers remain in the same order.
])
model.load_weights(cfg.c3d_model_weights)
```

Update `backend/classifier.py` to use current Keras APIs while retaining the existing architecture and MATLAB weight conversion.

### 4. Make local inference the default command

Refactor `backend/demo.py` into an explicit local CLI while preserving `run_demo()` for programmatic use.

Default behavior:

```bash
python demo.py --video input/in.mp4 --output-dir output
```

The command will:

- Validate input/model files.
- Decode the video and reject fewer than 16 frames with a clear message.
- Run feature extraction and classification.
- Save raw frame-level scores as `output/predictions.npy` for reproducibility.
- Save `output/out.gif`.
- Save selected anomaly frames using the existing score-delta rule.
- Print a concise summary with frame/clip counts, score range, and output paths.
- Perform no Firebase operation by default.

Optional upload behavior, if retained, will require an explicit `--upload-firebase` flag and compatible Firebase dependencies/configuration. It will not be exercised during this migration.

### 5. Modernize supporting utilities only where required

- `utils/video_util.py`: release the video capture and raise an actionable error if the video cannot be opened or decoded.
- `utils/array_util.py`: handle empty input and zero-norm feature vectors deliberately; retain 32-vector interpolation behavior.
- `utils/visualization_util.py`: remove module-global anomaly state, create deterministic per-run frame lists, avoid stale extracted-frame results, and use the Pillow GIF writer.
- `configuration.py`: keep default paths but allow CLI arguments to override the video/output paths.

Avoid changing the learned architecture, anomaly threshold semantics, or Firebase database schema.

### 6. Add focused automated checks and documentation

Add minimal tests for pure transformations and model loading/smoke behavior. Update `backend/README.md` with exact environment setup, model download, checksum verification, inference, expected outputs, and known CPU-performance limitations.

## Files and modules to create or modify

### Create

- `backend/requirements-ml.txt`.
- `backend/tests/test_array_util.py`.
- `backend/tests/test_models.py` or an equivalent lightweight smoke-test module.

### Modify

- `backend/c3d.py`.
- `backend/classifier.py`.
- `backend/demo.py`.
- `backend/configuration.py` if path handling needs a small compatibility adjustment.
- `backend/utils/video_util.py`.
- `backend/utils/array_util.py`.
- `backend/utils/visualization_util.py`.
- `backend/README.md`.
- `.gitignore` for `vigil_env`, generated scores, and model/cache artifacts.
- `research.md` and this plan as implementation facts become known.

### Add locally but do not commit

- `backend/vigil_env/`.
- `backend/trained_models/c3d_sports1m.h5`.

## API, UI, data, and integration changes

- Flask route behavior remains unchanged.
- `run_demo()` remains callable, but local output replaces unconditional Firebase upload.
- The anomaly model architecture and 32-feature bag contract remain unchanged.
- The CLI gains explicit input/output options and an optional upload flag.
- A NumPy prediction artifact is added for validation and reproducibility.
- No Firebase schema or browser dashboard changes are planned.

## Error handling and validation strategy

Provide direct errors for:

- Missing C3D/classifier weight files.
- Missing/unreadable input video.
- Video shorter than one complete 16-frame clip.
- Empty or non-finite extracted features/predictions.
- Legacy HDF5 topology mismatch.
- GIF writing failure.
- Requested Firebase upload without its optional dependencies/configuration.

Do not catch TensorFlow/model errors broadly; preserve their diagnostic context while adding file/path context where useful.

## Test and manual verification strategy

During implementation:

1. Continuously run Python compilation and focused unit tests.
2. Verify TensorFlow imports in `backend/vigil_env` and reports a CPU device.
3. Verify preprocessing produces `(1, 16, 112, 112, 3)`.
4. Verify classifier weights load and predict `(32, 1)` finite scores.
5. Verify C3D weights load without skipped/mismatched layers.
6. Run end-to-end inference on `input/in.mp4` with uploads disabled.
7. Confirm `predictions.npy` length equals decoded video frame count and values are finite.
8. Confirm `out.gif` is readable and extracted frames, if any, correspond to valid indexes.
9. Re-run Flask safe-mode route/asset tests inside the ML environment.
10. Run the documented commands from a clean shell in `backend/`.

## Risks and tradeoffs

- A 320 MB model download and a large TensorFlow installation are required.
- The old HDF5 file may expose a Keras 3 loader incompatibility despite matching architecture. If so, the narrow fallback is a one-time conversion with legacy Keras in an isolated environment, not a model replacement.
- CPU inference can be slow and memory intensive; correctness takes priority over optimization.
- OpenCV bicubic resizing may not be bit-identical to removed SciPy `imresize`, so exact historical scores may differ.
- There is no ground-truth output for the included video. Structural and sanity validation cannot establish model accuracy.
- Pinning tested versions improves reproducibility but will require periodic maintenance.

## Assumptions

- The documented public Sports-1M weights are the intended model artifact.
- CPU-only inference is acceptable on this Mac.
- The included `input/in.mp4` is the initial acceptance-test video.
- Local inference must not upload to Firebase unless explicitly requested.
- The existing anomaly heuristic remains in scope; retraining or accuracy improvement does not.
- No Git commit, branch, or push is requested.

## Review decision

The user approved downloading the documented public 320,010,428-byte C3D Sports-1M weight file and installing the modern ML dependencies into `backend/vigil_env`. Exact historical bit-for-bit predictions and a different private model artifact are not required.

## Implementation todo list

### Phase 1: Environment and model artifacts

- [x] Stop the currently running Flask development server before changing its environment or modules.
- [x] Add `vigil_env`, ML caches, downloaded weights, and generated prediction artifacts to `.gitignore`.
- [x] Create `backend/requirements-ml.txt` with a compatible pinned dependency set.
- [x] Create `backend/vigil_env` using Python 3.11.
- [x] Install and verify the ML dependency set in `backend/vigil_env`.
- [x] Download `sports1M_weights_tf.h5` to `backend/trained_models/c3d_sports1m.h5`.
- [x] Compute and record the downloaded model's SHA-256 checksum.

### Phase 2: Model compatibility migration

- [x] Port `backend/c3d.py` to modern TensorFlow/Keras imports and model construction.
- [x] Replace removed SciPy image resizing with OpenCV bicubic resizing while preserving dimensions.
- [x] Preserve the C3D topology/layer names and validate legacy HDF5 loading.
- [x] Port `backend/classifier.py` to modern TensorFlow/Keras APIs.
- [x] Validate MATLAB classifier weights and finite `(32, 1)` predictions.
- [x] Validate C3D preprocessing output shape and feature-extractor output shape.

### Phase 3: Safe local inference command

- [x] Refactor `backend/demo.py` into an explicit CLI with video/output arguments.
- [x] Make Firebase upload disabled by default and remove its unconditional dependency.
- [x] Save frame-level predictions to `output/predictions.npy`.
- [x] Add clear input, weight, frame-count, and finite-output validation.
- [x] Print a useful end-of-run inference summary.

### Phase 4: Supporting utilities

- [x] Update video loading to validate input and always release the OpenCV capture.
- [x] Update feature interpolation to handle empty and zero-norm input safely.
- [x] Remove global visualization state and stale extracted-frame behavior.
- [x] Switch GIF generation to the Pillow writer.
- [x] Preserve the existing anomaly score-delta heuristic.

### Phase 5: Tests and documentation

- [x] Add focused unit tests for array transformations and validation edge cases.
- [x] Add model/preprocessing smoke tests that avoid unnecessary full inference.
- [x] Update `backend/README.md` with exact environment, download, checksum, inference, output, and limitation details.
- [x] Update `research.md` with tested dependency versions and compatibility findings.

### Phase 6: End-to-end validation

- [x] Run Python compilation and the complete focused test suite.
- [x] Verify TensorFlow imports and CPU device discovery in `backend/vigil_env`.
- [x] Run full local inference on `backend/input/in.mp4` with Firebase disabled.
- [x] Verify finite frame-level scores, frame-count alignment, readable GIF output, and valid extracted frames.
- [x] Re-run safe Flask route and static-asset checks inside the ML environment.
- [x] Run all documented commands from the `backend/` working directory.
- [x] Run whitespace/error checks on changed text files.
- [x] Mark every completed todo in this plan.

