# Vigil Project Research

## Scope

This document records a repository-local analysis of `vigil_new`. The original research was completed before the backend reorganization. Backend paths described below now live under `backend/` unless a path is explicitly identified as a root-level research or standalone frontend artifact. No Firebase data or remote services were changed.

## System purpose and high-level behavior

Vigil is a prototype video-surveillance and emergency-response system. It combines:

1. A video anomaly-detection pipeline that scores frames from a local video.
2. Visualization code that produces an anomaly-score GIF and extracts suspicious frames.
3. Firebase Storage uploads for the generated visualization and selected frames.
4. A Flask web application that sends Firebase Cloud Messaging (FCM) notifications and renders an emergency dashboard.
5. A browser dashboard that reads live Firebase Realtime Database counters/statuses, displays Firebase Storage images, and lets an operator assign police, medical, or fire help.

The repository appears to be a prototype or hackathon-era application rather than a production-ready service. The machine-learning README pins a 2017–2018 Python ML stack, while the frontend references Bootstrap 4.4.1, Firebase JS 4.2.0, and Plotly 1.54.1-era output.

## Architecture and data flow

### 1. Video inference path

The intended offline flow starts at `demo.py:run_demo()`:

```text
input/in.mp4
    -> OpenCV frame decoding
    -> non-overlapping 16-frame clips
    -> C3D preprocessing and fc6 feature extraction (4,096 values/clip)
    -> interpolation into a fixed 32-feature bag
    -> dense anomaly classifier
    -> frame-level anomaly-score extrapolation
    -> output/out.gif plus output/fr*.png
    -> Firebase Storage uploads
```

Detailed behavior:

- `utils/video_util.py` decodes the complete video into memory as RGB frames.
- `utils/array_util.py:sliding_window()` groups frames into 16-frame clips with a stride of 16. A final partial clip may be produced, but `run_demo()` skips clips shorter than 16 frames.
- `c3d.py:preprocess_input()` samples 16 frames, resizes them to 128×171, subtracts a downloaded C3D mean tensor, center-crops to 112×112, and adds a batch dimension.
- `c3d.py:c3d_feature_extractor()` constructs the Sports-1M C3D network and exposes the 4,096-dimensional `fc6` layer.
- `utils/array_util.py:interpolate()` converts a variable number of clip features into exactly 32 normalized feature vectors.
- `classifier.py` builds a 4096 -> 512 -> 32 -> 1 dense model and loads MATLAB-format weights from `trained_models/weights_L1L2.mat`.
- `utils/array_util.py:extrapolate()` expands 32 predictions to one score per source frame.
- `utils/visualization_util.py:visualize_predictions()` creates an animated score plot. It treats a score increase greater than `0.05` between adjacent frames as a suspicious transition. If at least five such transitions exist, it saves every flagged frame as sequential `output/frN.png` files.
- `demo.py` uploads `output/out.gif` to `images/foo.jpg`, even though the local asset is a GIF and the remote extension is `.jpg`.

### 2. Flask and notification path

`app.py` exposes two routes:

- `GET /` renders `templates/home.html`, a single-button form.
- `POST /test` reads a hidden `action` form field, fetches every user from Firebase Realtime Database `/users`, and sends an FCM request to every stored `fcm_token`. It then calls `db_web()` and renders `templates/test.html`.

The FCM payload uses hard-coded values:

- Title: `Says`
- Body: `Important`
- Latitude: `13.054500`
- Longitude: `77.545590`
- Click action: form field `action`, currently `CONFIRM`

`run_demo()` is imported but commented out in the route. Consequently, submitting the Flask form does not perform new anomaly inference. `db_web()` only uploads existing `output/fr1.png` and `output/fr2.png` to `images/bar.jpg` and `images/foobar.jpg`.

### 3. Browser dashboard path

`templates/test.html` contains three distinct pieces:

- An emergency dashboard with counters and assignment controls.
- A large, fully embedded Plotly 1.54.1 library and static map visualization. This makes the file about 3.4 MB.
- A relative `firebase.js` script reference intended to connect the dashboard to Firebase.

The browser JavaScript in `static/images/firebase.js`:

- Listens to Realtime Database keys `Police`, `Medical`, and `FireDept`.
- Listens to `help/medical`, `help/police`, and `help/fire` assignment statuses.
- Loads Storage objects `images/foo.jpg`, `images/bar.jpg`, and `images/foobar.jpg` into the graph and frame elements.
- Writes `Assigned` when an operator selects a service.
- Resets all counters to `0` and all assignment states to `Unassigned`.
- Silently ignores all Storage download errors.

### 4. Components that are not integrated

- `data.csv` contains 2,089 timestamped rows with six activity indicator columns and latitude/longitude. The checked-in Python code never reads it. The embedded Plotly map appears to be a generated artifact rather than a runtime rendering of this CSV.
- `Temporal_Anomaly_Annotation_For_Testing_Videos/.../Temporal_Anomaly_Annotation.txt` contains anomaly labels and frame ranges from a video anomaly dataset. The application never reads it.
- `trained_models/model.json` describes a Keras 1.1.0 sequential model but is not read by the active classifier code.
- `db.py` is a standalone Firebase token-printing utility and is not imported by the application.
- `Website/` is a standalone copy of dashboard assets. Its active `test.html`, `styles.css`, and `firebase.js` are byte-for-byte duplicates of the corresponding template/static source files. `Website/previous/` is an older dashboard version.
- `Website.zip` is an archived website copy.

## Key files and modules

| Path | Responsibility | Important notes |
| --- | --- | --- |
| `README.md` | Minimal setup/run instructions | Lists exact legacy library versions; does not explain Flask/Firebase operation. |
| `configuration.py` | Model, input, and output paths | Paths are relative to the process working directory. The `classifier_model_weigts` name contains a typo used consistently by callers. |
| `parameters.py` | Frame and feature constants | Uses 16 frames per clip and 32 features per bag. Height/width/channel constants are currently unused. |
| `demo.py` | End-to-end video inference orchestration | Uses wildcard imports and uploads to a live Firebase project. |
| `c3d.py` | C3D network and video preprocessing | Relies on legacy Keras/SciPy APIs and a separately downloaded weight file. |
| `classifier.py` | Dense anomaly classifier and MATLAB weight conversion | Reconstructs the model in code; does not use `model.json`. |
| `utils/video_util.py` | OpenCV video loading and clip creation | Loads every frame into memory and does not explicitly release the capture. |
| `utils/array_util.py` | Sliding windows, interpolation, extrapolation | Contains an unregistered `test_interpolate()` helper. |
| `utils/visualization_util.py` | GIF generation and suspicious-frame extraction | Uses module-global mutable `lis`; output behavior depends on score deltas, not an absolute anomaly threshold. |
| `app.py` | Flask routes, FCM send, dashboard render | Performs synchronous remote calls in a request and contains an exposed FCM server key. |
| `db_web.py` | Firebase Storage upload helper | Uploads two fixed pre-existing frame files. |
| `templates/home.html` | Trigger form | The POST has no CSRF protection or authentication. |
| `templates/test.html` | Dashboard and embedded map | Duplicates a multi-megabyte Plotly runtime and uses unresolved relative asset URLs under Flask. |
| `static/images/firebase.js` | Dashboard Firebase integration | JavaScript is unusually stored under `static/images`; contains live Firebase configuration. |
| `static/css/styles.css` | Dashboard styling | Not referenced through Flask's static route. |
| `trained_models/weights_L1L2.mat` | Classifier weights | Present, about 8.5 MB. |
| `trained_models/c3d_sports1m.h5` | C3D weights | Required but absent and ignored by Git. |
| `input/in.mp4` | Demo input | Present, about 4.7 MB. |
| `output/` | Generated/demo artifacts | Contains a 7.5 MB GIF and eight frame images. |

## Dependencies and runtime expectations

There is no `requirements.txt`, lockfile, package metadata, container configuration, Makefile, CI configuration, or documented test command.

The README explicitly lists:

- Keras 2.2.0
- TensorFlow 1.10.1
- NumPy 1.14.5
- OpenCV 3.3.0.10
- SciPy 0.19.1
- Matplotlib 2.0.2

Imports show additional undeclared dependencies:

- Flask
- Requests
- `firebase` / `python-firebase`
- Pyrebase
- ImageMagick, required as Matplotlib's GIF writer

The checked-in `__pycache__` files reference CPython 3.7, suggesting at least one previous runtime used Python 3.7. The pinned TensorFlow and scientific stack are not expected to install cleanly on a current Python runtime without modernization or an old isolated environment.

Legacy compatibility hotspots include:

- `scipy.misc.imresize`, removed from modern SciPy.
- Older Keras module paths such as `keras.layers.convolutional` and `keras.utils.data_utils`.
- TensorFlow 1.x-era standalone Keras expectations.
- Pyrebase and `python-firebase` packages with overlapping Firebase roles.
- Firebase JS SDK 4.2.0 namespaced API.

## Existing patterns to preserve when extending the system

Until a modernization is explicitly in scope, focused changes should follow these project boundaries:

- Keep video decoding, array transformations, model construction, visualization, and web/Firebase integration in their existing modules.
- Reuse `configuration.py` and `parameters.py` for inference paths/constants rather than adding new literals elsewhere.
- Preserve the classifier's expected input shape: a bag of 32 vectors, each with 4,096 features.
- Preserve Firebase object/database names if compatibility with the existing mobile clients or deployed Firebase project is required.
- Treat `templates/` and `static/` as the Flask source of truth; `Website/` is duplicate/exported material unless the requested feature explicitly targets static hosting.
- Prefer Flask's `url_for('static', filename=...)` for application-served assets.
- Add targeted tests around pure array/video logic before changing inference behavior.

## Validation currently available

There is no automated test suite or type checker. Static parsing confirmed that all checked-in Python source files are syntactically valid under the available Python 3 parser.

Useful future validation layers are:

1. Unit tests for `sliding_window`, `interpolate`, and `extrapolate`.
2. Flask test-client coverage for `GET /` and mocked `POST /test` behavior.
3. A model smoke test using a short fixture video and mocked Firebase uploads.
4. Browser verification that Flask static assets resolve and dashboard listeners render expected Firebase snapshots.
5. A controlled integration test against a non-production Firebase project.

Running the application or inference pipeline was intentionally not used as a research probe because dependencies are undeclared, the C3D weights are missing, and imports/request handlers can access the live Firebase project or send notifications.

## Constraints and assumptions

- The repository is a fresh Git repository with no commits, so there is no local history to explain design decisions.
- The analysis treats `vigil_new` as the project root and assumes commands are run from that directory because all configuration paths are relative.
- The Firebase project may still be active. No remote reads/writes were performed during research.
- Firebase client configuration is normally public, but database/storage security still depends on server-side Firebase rules, which are not present here.
- The hard-coded legacy FCM server key is a server credential and must be treated as compromised because it is committed in source.
- The anomaly labels and CSV likely came from experimentation or dashboard generation, but their intended product role cannot be proven from the checked-in code.
- The mobile client that registers `/users/*/fcm_token` and reacts to `CONFIRM` is not included.

## Risks and important edge cases

### Security and external side effects

- `app.py` contains a hard-coded FCM server key. It should be revoked/rotated and replaced with environment-managed credentials before any deployment.
- The POST endpoint is unauthenticated and sends notifications to every registered user token.
- The dashboard directly writes operational Firebase state from the browser. Its safety depends entirely on Firebase rules, which are unknown.
- Flask debug mode is enabled in `app.py`.
- Firebase errors are generally unhandled or silently swallowed.

### Functional correctness

- Flask renders `/test`, but `styles.css`, `firebase.js`, and the icon paths are relative URLs. Flask has no routes for `/styles.css`, `/firebase.js`, or those root-level images, so the dashboard styling, live logic, and icons are expected to fail when served by this app.
- The icons exist under `Website/`, not Flask's `static/` tree.
- `run_demo()` is disabled in the request path. The UI displays or re-uploads stale checked-in output rather than analyzing a new video.
- `db_web()` assumes `output/fr1.png` and `output/fr2.png` exist.
- The GIF is uploaded with a `.jpg` object name, which may lead to incorrect content handling or confusing cache behavior.
- `visualize_predictions()` uses a module-global list that is never cleared. Multiple runs in one process accumulate old frame indexes.
- Extracted frame files from earlier runs are not cleaned up. A later low-anomaly run can leave stale frames available for upload.
- An anomaly decision is based on the count of positive score jumps, not score magnitude or contiguous anomalous intervals.
- `interpolate()` can divide by zero before checking the resulting norm and fails on an empty feature list. Empty videos or videos shorter than 16 frames can therefore break inference.
- `app.py` assumes `firebase.get('/users', '')` returns a dictionary and each record contains `fcm_token`.
- Requests to FCM have no timeout, exception handling, retry policy, or response validation.

### Maintainability and performance

- The full video is loaded into RAM before inference.
- Models are rebuilt and weights reloaded on every `run_demo()` call.
- Inference, GIF rendering, network upload, broadcast notification, and page rendering are synchronous operations.
- Wildcard imports obscure dependencies and expose names transitively.
- The same Firebase configuration and duplicate website assets exist in multiple files.
- Generated assets, Python bytecode, input media, and output media are committed or unignored.
- The 3.4 MB HTML template embeds an entire minified Plotly build and a static data visualization, making normal template maintenance difficult.

## Open questions

These questions should be resolved during planning for any feature that touches the relevant area:

1. Is the primary goal to restore the original prototype exactly, modernize it, or build a production successor?
2. Must the existing Firebase project, database schema, Storage object names, and mobile notification contract remain compatible?
3. Is `input/in.mp4` fixed demo content, or should users/cameras upload or stream videos?
4. Should anomaly inference be synchronous, background-job based, batch based, or real time?
5. What is the intended anomaly decision policy: absolute score threshold, change threshold, duration, or trained event class?
6. Should the embedded crime map and `data.csv` remain part of the product?
7. Is `Website/` a deployment target or only an obsolete duplicate/export?
8. Are the original C3D weights available, and is reproducing the old model's output a requirement?
9. What Firebase security rules and authentication model are expected?
10. Which Python/OS/GPU environment must be supported?

## Implemented project boundary

The repository now separates the active runtime from standalone and research artifacts:

- `backend/` owns the Flask server, anomaly pipeline, runtime models/media, templates, and Flask static assets.
- `Website/` remains the standalone dashboard export.
- `data.csv` and `Temporal_Anomaly_Annotation_For_Testing_Videos/` remain root-level research datasets because active backend code does not load them.
- Backend commands run from `backend/` so the legacy relative model/input/output paths continue to resolve.

## Recommended implementation surface area

Because no feature has been specified, no code changes are recommended yet. Future work should select the smallest relevant surface:

- **Inference-only work:** `demo.py`, `c3d.py`, `classifier.py`, `configuration.py`, `parameters.py`, and `utils/`.
- **Flask/API work:** `app.py`, `db_web.py`, `templates/`, and Flask-owned `static/` assets.
- **Dashboard work:** `templates/test.html`, `static/css/styles.css`, and a relocated/renamed dashboard JavaScript file under `static/`.
- **Firebase/notification work:** isolate credentials/configuration first, then update `app.py`, `db_web.py`, and browser Firebase integration together while preserving any required schema contract.
- **Reproducibility work:** add a dependency manifest, environment documentation, secrets template, test structure, and generated-artifact ignore rules before broader refactoring.
- **Model modernization:** treat this as a dedicated migration with golden-output comparisons; do not combine it casually with UI or notification changes.

Future feature work should continue using a feature-specific `plan.md`, feedback, a detailed todo list, and explicit implementation approval.

## Local ML modernization research (October 2026)

### Target machine

- Apple Silicon (`arm64`).
- macOS 15.1.1.
- CPython 3.11.3.
- ImageMagick is installed as `/opt/homebrew/bin/magick`.
- Flask, Requests, NumPy 1.26.4, OpenCV 4.7.0, SciPy 1.14.0, and Matplotlib 3.9.1 exist in the global interpreter, but TensorFlow/Keras and the Firebase Python packages do not.

TensorFlow's official pip installation documentation lists macOS ARM64 CPU wheels for Python 3.11 and identifies TensorFlow 2.21 as the current wheel in that compatibility table. macOS has no official TensorFlow GPU support, so this project should target CPU inference. Keras 3 documents broad Keras 2 compatibility and support for legacy HDF5 weight files when the architecture is reconstructed with built-in layers.

### Available and missing model artifacts

- `backend/trained_models/weights_L1L2.mat` is present (8,457,152 bytes). Its arrays match the checked-in classifier topology:
  - `(4096, 512)` kernel and `(512,)` bias.
  - `(512, 32)` kernel and `(32,)` bias.
  - `(32, 1)` kernel and `(1,)` bias.
- `backend/trained_models/model.json` is present but unused by the active code.
- `backend/trained_models/c3d_sports1m.h5` is missing.
- The repository's documented public GitHub release URL is still valid and serves `sports1M_weights_tf.h5`, a 320,010,428-byte HDF5 file. It is the intended TensorFlow-backend C3D Sports-1M weight artifact.
- `c3d_mean.npy` is also downloaded at runtime by the current code. Modern `keras.utils.get_file`/`tf.keras.utils.get_file` still supports a verified file hash and explicit cache location.

No private or user-provided model appears necessary if downloading the documented public C3D weights is acceptable.

### Required code migrations

- Replace standalone legacy Keras imports with a consistent modern TensorFlow/Keras API.
- Replace removed `scipy.misc.imresize` with `cv2.resize(..., interpolation=cv2.INTER_CUBIC)` while preserving the expected `(128, 171)` image dimensions.
- Build Sequential models with explicit `keras.Input` layers rather than deprecated `input_dim`/`input_shape` arguments.
- Ensure the classifier is built before applying the converted MATLAB weights.
- Use `model.predict(..., verbose=0)` for current Keras inference.
- Remove wildcard imports so dependencies and configuration ownership are explicit.
- Remove unconditional `pyrebase` import and make Firebase upload an explicit opt-in path. Local inference must only create local output.
- Reset anomaly-frame state per run instead of retaining the module-global `lis` list.
- Create output directories when needed and release OpenCV video handles.
- Fail early with actionable errors for a missing video, missing weights, unreadable video, or fewer than 16 decoded frames.
- Prefer Matplotlib's Pillow writer for GIF output so inference does not depend on an external ImageMagick binary.
- Add a dedicated ML dependency manifest and keep it separate from the minimal web manifest.

### Performance expectations

The C3D network contains large 3D convolutions and two 4,096-unit dense layers. On Apple Silicon it will run through TensorFlow's CPU backend under the officially supported installation path. Model loading and processing the included 4.7 MB video may take substantial time and memory. The model should be constructed once per command invocation, not once per clip.

### Validation requirements

- Install into a project-local virtual environment rather than the global Python installation.
- Verify TensorFlow imports and reports the CPU device.
- Validate C3D preprocessing shape `(1, 16, 112, 112, 3)`.
- Validate classifier weight loading and output shape `(32, 1)`.
- Validate C3D HDF5 loading before running full video inference.
- Run the complete included `input/in.mp4` demo with remote upload disabled.
- Confirm generated predictions are finite, match the video frame count after extrapolation, and produce a readable GIF.
- Re-run the Flask safe-mode checks in the combined ML environment to ensure web behavior is preserved.

### Modernization risks and unknowns

- Legacy HDF5 compatibility is documented generally, but the exact 2017 C3D file must be tested against the reconstructed modern architecture. Layer/kernel layout mismatch is the largest technical risk.
- Replacing SciPy's resize function with OpenCV may produce small numeric differences, even with bicubic interpolation.
- There is no golden prediction output or expected anomaly score file, so validation can prove operational correctness and output shape/range, not exact historical equivalence.
- CPU inference may be slow. Performance optimization is outside the initial compatibility scope.
- The public model download is approximately 320 MB and requires user approval before adding it to the local workspace.

### Tested modernization result

The approved migration was validated on the target machine with this pinned environment:

- TensorFlow 2.21.0 and Keras 3.15.1.
- NumPy 1.26.4 and SciPy 1.14.1.
- OpenCV headless 4.10.0.84.
- Matplotlib 3.9.2, Pillow 11.0.0, and h5py 3.12.1.

The legacy C3D HDF5 file loaded directly into the reconstructed 79,991,015-parameter modern Keras model without layer mismatches. The feature extractor produced finite `(1, 4096)` features. The MATLAB classifier weights produced finite `(32, 1)` outputs.

End-to-end CPU inference on `backend/input/in.mp4` decoded 1,159 frames into 72 complete clips. It produced 1,159 finite frame scores ranging from approximately `0.00000153` to `0.99999970`, a readable 116-frame GIF, and six extracted anomaly-transition frames. Firebase upload was disabled.

Downloaded artifact checksums:

- `c3d_sports1m.h5`: SHA-256 `c4d321e098d37c1585218dffe577c260f834fbbc8d9cb7950f0c3c165e1e93ce`.
- `c3d_mean.npy`: SHA-256 `5dee0b56fb6782efbbad765ff33de49201bbee77d897b646525cae4058cd1e12` (also verified by the original MD5 configured in code).

## Demo website research (superseded visual reference)

### Reference analysis

The requested demo combines two distinct references and should borrow from each without copying either site.

**Ambient.ai content/product cues**

The [Ambient.ai homepage](https://www.ambient.ai/) positions computer vision as an always-on physical-security intelligence layer. Its strongest applicable patterns are:

- Lead with the security outcome rather than model architecture.
- Frame the product as helping operators see relevant activity, investigate quickly, and respond before escalation.
- Show the system through real surveillance imagery and product output rather than decorative illustrations.
- Organize the story around detection, investigation, and response.
- Use proof-oriented metrics sparingly and close to the product demonstration.

Ambient's separate demo is essentially a sample library plus a clear run/analysis state. For Vigil's current maturity, a pre-generated evidence viewer is more honest and reliable than implying real-time browser inference.

**Fort Sec visual cues**

The [Fort Sec Dribbble concept](https://dribbble.com/shots/25551213-Fort-Sec-Cyber-Security-Website) establishes a premium editorial security style:

- Near-black textured backgrounds.
- Oversized high-contrast serif display typography paired with quiet sans-serif utility text.
- Cool gray copy and hairline borders instead of bright white blocks.
- Sparse violet, blue, and magenta glow accents.
- Large negative space and asymmetric two-column compositions.
- Rounded rectangular cards with subtle translucent surfaces.
- Underlined text links and compact pill controls.

The reference palette explicitly includes `#050506`, `#B2B5C4`, `#7688C1`, `#293056`, `#A1ABC8`, `#5B5FB3`, `#404A6B`, and `#8F57BE`. Vigil should use a restrained subset rather than reproducing the complete reference.

### Current demo assets

The current `backend/output/` directory contains everything required for a read-only demo:

- `out.gif`: a 600×600, 116-frame animated visualization combining video and anomaly scores.
- `predictions.npy`: 1,159 finite frame-level anomaly scores.
- `fr0.png` through `fr5.png`: six extracted incident frames.

Validated source-video facts:

- 1,159 decoded frames.
- 30 frames per second.
- Approximately 38.6 seconds.
- 72 complete 16-frame clips analyzed.
- Six score increases above the existing `0.05` incident-frame heuristic.
- Score range approximately `0.00000153` to `0.99999970`.

The GIF and extracted frames are generated artifacts and should remain the visual source of truth. The page should not pretend to provide live camera monitoring, production-grade alert classification, or model accuracy metrics that the repository cannot substantiate.

### Existing web implementation

The current Flask web surface is unsuitable as the new demo:

- `/` is only a Bootstrap form with a Submit button.
- `POST /test` renders a 3.4 MB legacy template with an embedded Plotly runtime and unrelated static crime map.
- The legacy dashboard is coupled to Firebase counters and emergency-service assignment controls.
- Current CSS is a small Bootstrap-era stylesheet with fixed assumptions and inline layout values.
- The app already has a safe local mode, but the demo output is not exposed through a controlled Flask route.

The new demo should replace the primary web experience instead of styling the legacy page. Firebase notification and assignment behavior is not required to demonstrate the local anomaly model.

### Recommended minimal information architecture

A single responsive page is sufficient:

1. **Header:** Vigil wordmark and two anchor links (`How it works`, `Detection demo`).
2. **Hero:** one outcome-led headline, one short supporting paragraph, and one CTA that scrolls to the demo.
3. **Detection demo:** the generated GIF as the focal artifact, compact run metadata, and the six extracted incident frames as selectable thumbnails.
4. **How it works:** three concise steps—monitor, score, surface—without broad marketing content.
5. **Footer:** project name and a local-demo disclaimer.

No testimonials, fake customer logos, pricing, contact form, account flow, Firebase actions, blog, or large solution catalog are justified.

### Data and route design

- `GET /` renders the single demo page.
- `GET /output/<filename>` serves only files from `backend/output/` through Flask's safe directory handling.
- The inference command should create `output/summary.json` with display-safe metadata so the web app can use the Python standard library instead of importing NumPy at request time.
- The Flask app should tolerate a missing summary, GIF, or frame set and render an actionable empty state with the command needed to generate them.
- The existing `POST /test` Firebase route should be removed from the primary demo surface. If legacy behavior needs preservation, it should be deliberately retained under a clearly named legacy route; there is currently no demo requirement for it.

### UI and accessibility constraints

- Use semantic HTML, visible focus states, descriptive alternative text, and sufficient contrast.
- Respect `prefers-reduced-motion`; the GIF itself cannot be paused by CSS, so provide an explicit play/pause control that swaps the animated GIF for the first extracted still.
- Avoid external JavaScript frameworks and Bootstrap. A small local script is enough for thumbnail selection, animation control, and smooth in-page navigation.
- Use CSS gradients/noise effects rather than adding decorative image dependencies.
- Support desktop and mobile layouts without horizontal overflow.

### Recommended implementation surface

- Replace `backend/templates/home.html` with the single-page demo.
- Replace `backend/static/css/styles.css` with the new responsive visual system.
- Add `backend/static/js/demo.js` for the small interaction layer.
- Simplify `backend/app.py` to serve the page and generated output safely.
- Update `backend/demo.py` to write `summary.json` after successful inference.
- Add focused Flask tests for asset availability, output serving, metadata, and missing-output behavior.
- Remove or archive the legacy `test.html` only after scope confirmation; it should not remain part of the primary route flow.

### Open questions

1. Should the website remain a read-only showcase of the pre-generated output (recommended), or should users upload a video and trigger inference from the browser?
2. Should the visible product name remain `Vigil`, or use the existing dashboard label `Vigilant`?

The questions above were resolved by the user: the product name is `Vigil`, Firebase/legacy UI should be ignored, and the website needs both pre-generated demos and user-uploaded testing. The Fort Sec visual analysis above is retained only as research history and is not the implementation direction.

## Revised demo website research: DOTDNA reference

### Correct visual reference

The implementation should use the [DOTDNA Cybersecurity Landing Page](https://dribbble.com/shots/26619267-DOTDNA-Cybersecurity-Landing-Page) as its visual reference, not Fort Sec.

The corrected design has these defining traits:

- Nearly black green canvas (`#010301`) with a subtle forest-green outer atmosphere.
- Large rounded application frame occupying most of the viewport.
- Oversized centered sans-serif headline with tight leading and restrained width.
- Bright acid/neon green (`#25B103`) used only for identity, active state, dots, and a primary action.
- White/green particle cluster as the focal technical motif.
- Fine curved/perspective green lines crossing the lower half of the screen.
- Three low-contrast information columns with only the active/central item fully legible.
- Floating rounded navigation pill centered near the bottom edge.
- Minimal top chrome: compact wordmark at left, one rounded action at right.
- No serif display typography, violet glow, glass illustration cards, or cool-gray editorial treatment.

Relevant published palette values are `#010301`, `#364A32`, `#DFFCE8`, `#5B6559`, `#A4C1AA`, `#778676`, and `#25B103`. Vigil should adopt the contrast relationships and spatial system without copying DOTDNA's logo, language, or proprietary graphic.

### Confirmed product scope

The website is a two-mode local application:

1. **Demo tab:** browse pre-generated Vigil analysis in `backend/output/`.
2. **Test tab:** upload a local video, run the existing C3D anomaly pipeline on the backend, and inspect that run's GIF, score metadata, and surfaced frames.

The visible product name is `Vigil`. Existing Firebase notification code, emergency-service controls, Plotly map, Bootstrap UI, and legacy `/test` dashboard are out of scope and can be removed.

### Upload inference constraints

Full inference on the included 38.6-second video takes roughly one minute on the target Apple Silicon CPU. A minimal local demo can use a synchronous HTTP request with an explicit `Analyzing…` state because there is no reverse proxy or multi-user production SLA. It should not imply instantaneous processing.

Recommended safety boundaries:

- Accept `.mp4`, `.mov`, `.avi`, and `.mkv` files.
- Enforce a 100 MB request limit.
- Use a generated job ID rather than the original filename for filesystem paths.
- Store each result under `backend/output/runs/<job-id>/`.
- Save the upload in a temporary job directory and remove it after success or failure.
- Serialize inference with a process-local lock; TensorFlow model execution should not overlap in this local demo.
- Lazy-load and cache the C3D feature extractor and classifier once per Flask process to avoid repeated 320 MB model loading.
- Return structured JSON on success or failure.
- Do not enable Firebase upload from the web endpoint.

This is intentionally a local demonstration architecture. Production deployment would require a background job queue, persistent object storage, authentication, abuse controls, rate limiting, malware scanning, lifecycle cleanup, observability, and a production WSGI server.

### Revised route and state model

- `GET /`: render the two-tab application shell; `Demo` is active by default.
- `GET /api/demo`: return metadata and URLs for the pre-generated output.
- `POST /api/analyze`: validate multipart video input, run local inference, and return a result payload.
- `GET /output/<path:filename>`: safely serve demo/run artifacts below `backend/output/`.

No database is required. A result payload can be assembled from each job's `summary.json`:

```json
{
  "job_id": "generated-id",
  "frame_count": 1159,
  "duration_seconds": 38.63,
  "complete_clips": 72,
  "score_min": 0.00000153,
  "score_max": 0.99999970,
  "surfaced_frames": ["fr0.png", "fr1.png"],
  "analysis_url": "/output/runs/generated-id/out.gif"
}
```

### Interaction model

- Floating pill navigation contains `Demo` and `Test`, with neon-green active state.
- Demo mode opens with the generated analysis and thumbnails already available.
- Test mode contains one drag-and-drop/file-picker surface and concise file constraints.
- After selection, show filename/size and require an explicit `Analyze video` action.
- While processing, disable repeat submission and show an honest indeterminate progress state with elapsed time.
- On completion, reuse the exact same result viewer component as Demo mode.
- On error, keep the selected filename visible, show the server message, and permit retry.
- Thumbnail clicks swap the central preview; `View analysis` restores the GIF.

### Updated implementation surface

- Replace `backend/app.py` with the two-mode demo/upload API and cached inference service.
- Extend `backend/demo.py` to accept injected models, return structured summary data, and write `summary.json`.
- Replace `backend/templates/home.html`.
- Replace `backend/static/css/styles.css`.
- Add `backend/static/js/app.js`.
- Remove `backend/templates/test.html`, Firebase JavaScript, and unused emergency icons.
- Add route, upload-validation, inference-mocking, metadata, and traversal tests.
- Keep real end-to-end model validation as an explicit manual/integration check, not a per-request unit test.

### Implemented website result

The corrected DOTDNA-inspired Demo/Test website was implemented and validated locally:

- Flask now exposes `/`, `/api/demo`, `/api/analyze`, and safe `/output/<path>` serving.
- Importing the Demo web application does not load TensorFlow. Models are lazy-loaded on the first Test request and cached afterward.
- Test uploads use UUID paths, accept MP4/MOV/AVI/MKV up to 100 MB, serialize inference, delete source uploads, and retain isolated output runs.
- Inference writes `summary.json` atomically and returns one shared result schema for Demo and Test.
- The active page contains no Bootstrap, Plotly, Firebase, emergency dispatch UI, or legacy `/test` dependency.
- The root-level standalone `Website/` archive remains unchanged.

Automated validation increased to 22 passing tests. A real HTTP upload of `input/in.mp4` completed successfully with 1,159 frames, 72 complete clips, finite scores, six surfaced moments, and isolated GIF/PNG/JSON/NumPy artifacts.

Desktop and mobile screenshots were rendered with a headless Chromium browser and inspected. The final interface uses the corrected deep black-green frame, acid-green accent, centered oversized sans-serif headline, particle signal, perspective lines, subdued method columns, floating Demo/Test pill, responsive result viewer, and responsive upload surface.

Browser interaction checks verified:

- Demo loading.
- Surfaced-frame selection and GIF restoration.
- Keyboard arrow navigation between tabs with correct ARIA state.
- Local video selection and Analyze-button enablement.
- Reduced-motion media-query behavior.

## Themed analysis GIF research (October 2026)

### Current rendering path

`backend/demo.py` saves frame-level predictions and calls `utils.visualization_util.visualize_predictions()`. That function decodes the video a second time, validates one prediction per frame, deletes stale `fr*.png` files, preserves the existing score-delta anomaly heuristic, and writes `out.gif` with Matplotlib's `FuncAnimation` and `PillowWriter`.

The current GIF is a generic 600 × 600 Matplotlib figure with two equal stacked plots. The video pane carries only a default `Monitored Video` axis label, while the score pane uses default white styling, blue linework, visible axes, and `Frame Number` / `Anomaly Score` labels. It samples every tenth source frame and writes 116 frames at 10 FPS for the included 1,159-frame video.

### Relevant Vigil visual system

The active UI defines a consistent black-green system in `backend/static/css/styles.css`:

- canvas/surface: `#010301`, `#020702`, and `#071007`;
- borders/grid: `#364A32` and translucent variants;
- primary text: `#DFFCE8`;
- muted text: `#A4C1AA` and `#778676`;
- signal accent: `#25B103` and `#50E326`;
- warning/error accent: `#FF806D`.

The browser places the GIF inside a wide, dark result viewer. A landscape artifact will use that space more effectively than the present square output.

### Recommended renderer changes

Keep the inference, score values, output filename, frame sampling, anomaly heuristic, extracted-frame behavior, API schema, and CLI unchanged. Limit the implementation to `backend/utils/visualization_util.py`, focused visualization tests, and output documentation.

The new GIF should use a 16:9 dark canvas with:

- a left column with a large video stage, rounded-looking dark framing, and no Matplotlib axes;
- the surfaced anomaly frames in a compact thumbnail strip directly below the video;
- a dedicated anomaly graph and score panel in the right column;
- a compact Vigil status rail containing product label, frame progress, and live score;
- a signal panel using the website's green palette, subtle grid, filled score trace, current-position marker, and a clear high-risk threshold;
- restrained text and glow-like accents that remain readable after GIF palette conversion;
- stable layout created once, with only image, line, fill/marker, and text content updated per animation frame.

### Constraints and risks

- GIF palette compression can flatten subtle gradients and glows, so contrast must not rely on low-opacity detail alone.
- Increasing resolution materially increases render time and file size. A moderate landscape resolution and the existing one-in-ten sampling are preferable to a high-resolution export.
- Matplotlib artist accumulation is a risk if a new fill object is created every frame; dynamic artists must be removed or updated deterministically.
- Tests should inspect layout/style helpers and a tiny generated GIF rather than rerun model inference.
- The previously generated `backend/output/out.gif` will not change until the user reruns `demo.py`; generated artifacts remain ignored by Git.

### Open questions

No model weights or inference inputs are needed for this change. The existing Vigil palette and current GIF contract provide enough information to implement a focused visual refresh.

### User layout feedback

The reviewed mock established the final information hierarchy: video at upper left, detected-frame thumbnails immediately below the video, and the graph on the right. The production renderer should follow this arrangement rather than placing the graph below the video.

### Implemented GIF result

The production renderer now follows the approved mock in `backend/utils/visualization_util.py`. It creates a 16:9 Vigil dashboard with the monitored feed and up to six representative detected moments on the left, plus live confidence, status, threshold, evolving signal, model identity, and timeline progress on the right. The nearest detected moment receives a green border as playback advances. When the existing heuristic surfaces fewer than five moments, the thumbnail region shows a quiet empty state.

The renderer updates existing Matplotlib image, line, marker, polygon, text, border, and progress artists rather than accumulating artists per frame. Figure cleanup now occurs in `finally` blocks for both visualization functions.

Focused tests cover the landscape layout, palette, thumbnail placement, signal styling, generated GIF readability, frame extraction, and anomaly-index preservation. The complete suite passes with 24 tests. The existing saved predictions were used to regenerate `backend/output/out.gif` without rerunning model inference: the result is a readable 960 × 540, 116-frame GIF of approximately 6.7 MB with all six detected moments. First and mid-animation frames were visually inspected for palette quality and dynamic state correctness.

## Dashboard reference UI research (October 2026)

### Reference artifact

The user supplied `Vigil_ Video Anomaly Intelligence Dashboard.png`, a 1536 × 1024 composite product mockup. It contains one landing-page hero and two desktop application states. It should guide visual hierarchy, density, layout, and interaction framing, while the implemented site must remain truthful to Vigil's existing Demo/Test capabilities.

The reference establishes:

- a full-viewport black-green background with a concentrated green glow behind content;
- thin olive-green borders, 14–20 px card radii, and compact spacing rather than the current oversized editorial sections;
- a short horizontal header with the Vigil mark, a local-CPU badge, and sparse text navigation;
- a centered hero with a two-line headline, small eyebrow, two prominent CTAs, local-processing reassurance, and faint curved signal lines;
- an application shell with a narrow left sidebar, compact page heading, dense cards, and bright green active controls;
- a two-column analysis detail layout where media/chart evidence occupies the main area and run metadata occupies a narrow side rail;
- small uppercase labels, neutral sans-serif typography, high-information density, and green/red/amber state accents.

### Current web application

The current Flask surface already provides the relevant behavior:

- `GET /` renders `templates/home.html`.
- `GET /api/demo` returns the pre-generated GIF, summary metrics, and detected-frame URLs.
- `POST /api/analyze` validates and processes an uploaded video.
- `static/js/app.js` owns Demo/Test navigation, upload validation, processing state, result rendering, detected-frame selection, and GIF restoration.

The current page is visually more editorial than the new reference. It uses a tall hero, decorative particle cluster, three large method columns, an oversized workspace, and a floating bottom pill for Demo/Test. The result viewer is already compatible with the necessary data, but its page framing and spacing do not match the denser dashboard reference.

### Functional boundaries

The reference shows Incidents, Evaluation, confirm/false-positive actions, severity labels, calibrated confidence, and semantic incident details. Vigil does not currently produce or store those concepts. Adding visually active but nonfunctional controls would misrepresent the system and contradict the minimal-demo scope.

The redesign should therefore map only real functionality:

- `Sample analysis` maps to the existing Demo mode.
- `Analyze video` maps to the existing Test/upload mode.
- detected moments map to the current surfaced score-transition frames.
- run details map to duration, frames, temporal clips, peak score, and moment count.
- the generated 16:9 `out.gif` remains the primary analysis visualization.

No API, inference, storage, or schema change is required.

### Recommended implementation surface

- Rewrite `backend/templates/home.html` into a compact hero followed by a dashboard shell.
- Replace `backend/static/css/styles.css` with the reference-driven layout and responsive states.
- Make small, targeted changes to `backend/static/js/app.js` for hero CTA navigation and the revised sidebar tab controls.
- Extend the existing Flask HTML test with required structure and legacy/dependency exclusions.
- Keep `backend/app.py`, APIs, inference, result payloads, and generated artifacts unchanged.

### Responsive interpretation

The desktop reference assumes a wide viewport. On tablets, the dashboard sidebar should become a compact horizontal mode switch, and the analysis grid should stack. On phones, hero CTAs should become full-width, upload/result cards should use one column, metrics should remain readable, and detected moments should scroll horizontally. Keyboard tabs, visible focus, ARIA state, and reduced-motion behavior must remain intact.

### Risks and assumptions

- The composite reference is not a literal screen specification; the implementation should reproduce its design system and hierarchy rather than fake unavailable product features.
- The GIF already contains a chart and detected moments, so surrounding UI should avoid excessive duplication while still exposing selectable source frames and factual run metrics.
- The supplied PNG is a design reference only and should not be embedded as a website asset.
- Existing Demo/Test URLs, upload constraints, and local-only processing behavior remain unchanged.
- No server should be started automatically; validation can use Flask's test client and browser rendering only when explicitly approved.

### Implemented dashboard result

The active Flask UI now follows the supplied dashboard reference while keeping the existing feature boundary. The page uses a compact product header and hero, real Analyze/Sample Analysis CTAs, a three-step workflow strip, desktop sidebar navigation, dense upload cards, and a dashboard result viewer with the analysis artifact and selectable evidence frames in the main column plus factual run details in the right rail.

The sidebar collapses into a horizontal mode switch on smaller screens, the analysis details stack below the media, and evidence frames become horizontally scrollable on phones. Hero CTAs reuse the same ARIA tab activation path as sidebar navigation. No incident CRUD, severity classification, evaluation history, or confirmation actions were added.

Validation completed without starting a server: JavaScript syntax passed, Python compilation passed, dependency checks found no broken packages, `git diff --check` passed, and all 24 automated tests passed.
