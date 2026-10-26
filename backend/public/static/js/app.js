(() => {
  const app = document.querySelector("#app");
  const tabs = [...document.querySelectorAll("[role='tab']")];
  const heroActions = [...document.querySelectorAll("[data-tab-target]")];
  const panels = {
    demo: document.querySelector("#panel-demo"),
    test: document.querySelector("#panel-test"),
  };
  const demoHost = document.querySelector("#demo-content");
  const testHost = document.querySelector("#test-content");
  const statusHost = document.querySelector("#test-status");
  const form = document.querySelector("#upload-form");
  const input = document.querySelector("#video-input");
  const dropZone = document.querySelector("#drop-zone");
  const selectedFile = document.querySelector("#selected-file");
  const fileName = document.querySelector("#file-name");
  const fileSize = document.querySelector("#file-size");
  const removeFile = document.querySelector("#remove-file");
  const analyzeButton = document.querySelector("#analyze-button");
  const resultTemplate = document.querySelector("#result-template");
  const allowedExtensions = [".mp4", ".mov", ".avi", ".mkv"];
  const maxBytes = 100 * 1024 * 1024;
  const detectionCategory = document.querySelector("#detection-category");
  const detectionCategories = [
    "Abuse", "Arrest", "Arson", "Assault", "Road Accident", "Burglary",
    "Explosion", "Fighting", "Robbery", "Shooting", "Stealing", "Shoplifting",
    "Vandalism",
  ];
  let currentFile = null;
  let elapsedTimer = null;
  const reportCache = new Map();

  if (detectionCategory) {
    let categoryIndex = 0;
    let characterIndex = 0;
    let deleting = false;
    detectionCategory.textContent = "";

    function typeDetectionCategory() {
      const category = detectionCategories[categoryIndex];
      characterIndex += deleting ? -1 : 1;
      detectionCategory.textContent = category.slice(0, characterIndex);

      let delay = deleting ? 42 : 78;
      if (!deleting && characterIndex === category.length) {
        deleting = true;
        delay = 1100;
      } else if (deleting && characterIndex === 0) {
        deleting = false;
        categoryIndex = (categoryIndex + 1) % detectionCategories.length;
        delay = 260;
      }
      window.setTimeout(typeDetectionCategory, delay);
    }

    typeDetectionCategory();
  }

  function activateTab(name, focus = false, shouldScroll = true) {
    tabs.forEach((tab) => {
      const active = tab.dataset.tab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    });
    Object.entries(panels).forEach(([key, panel]) => {
      const active = key === name;
      panel.hidden = !active;
      panel.classList.toggle("is-active", active);
    });
    if (shouldScroll) panels[name].scrollIntoView({ behavior: "smooth", block: "start" });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateTab(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      activateTab(next.dataset.tab, true);
    });
  });

  heroActions.forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
  });

  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return "—";
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
  }

  function formatScore(score) {
    if (score === null || score === undefined) return "—";
    return Number(score).toFixed(3);
  }

  function addMetric(list, label, value) {
    const row = document.createElement("div");
    row.className = "metric";
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    row.append(term, detail);
    list.append(row);
  }

  function renderEmpty(host, message) {
    host.replaceChildren();
    const state = document.createElement("div");
    state.className = "empty-state";
    const title = document.createElement("strong");
    const copy = document.createElement("p");
    title.textContent = "No demo output yet";
    copy.textContent = message || "Run python demo.py from the backend to generate evidence.";
    state.append(title, copy);
    host.append(state);
  }

  function populateIncidentReport(viewer, report) {
    viewer.querySelector(".incident-summary").textContent = report.incident_summary;
    viewer.querySelector(".incident-timestamp").textContent = report.timestamp;
    viewer.querySelector(".evidence-note").textContent = report.evidence_note;
    viewer.querySelector(".incident-limitations").textContent = report.limitations;
    [
      [".visual-observations", report.visual_observations],
      [".supporting-evidence", report.supporting_evidence],
      [".recommended-steps", report.recommended_next_steps],
    ].forEach(([selector, items]) => {
      const list = viewer.querySelector(selector);
      list.replaceChildren();
      (items || []).forEach((item) => {
        const row = document.createElement("li");
        row.textContent = item;
        list.append(row);
      });
    });
  }

  async function loadGemmaReport(viewer, result) {
    if (!result.id) return;
    const badge = viewer.querySelector(".review-badge");
    if (reportCache.has(result.id)) {
      populateIncidentReport(viewer, reportCache.get(result.id));
      badge.textContent = "Gemma report · Needs review";
      return;
    }
    badge.textContent = "Generating Gemma report…";
    try {
      const response = await fetch("/api/incident-report", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ id: result.id }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Report generation failed.");
      reportCache.set(result.id, payload.incident_report);
      if (viewer.isConnected) {
        populateIncidentReport(viewer, payload.incident_report);
        badge.textContent = "Gemma report · Needs review";
      }
    } catch (error) {
      if (viewer.isConnected) {
        badge.textContent = "Fallback report · Needs review";
        badge.title = error.message;
      }
    }
  }

  function renderResult(host, result) {
    host.replaceChildren();
    const fragment = resultTemplate.content.cloneNode(true);
    const viewer = fragment.querySelector(".result-viewer");
    const preview = fragment.querySelector(".preview-image");
    const metrics = fragment.querySelector(".metrics");
    const report = result.incident_report || {
      incident_summary: result.description,
      timestamp: "Flagged interval",
      visual_observations: [result.description],
      supporting_evidence: ["Review the generated analysis visualization."],
      evidence_note: "",
      recommended_next_steps: ["Review the original footage around the flagged interval."],
      limitations: "The available output requires human review.",
    };
    const location = fragment.querySelector(".run-location");
    const camera = fragment.querySelector(".run-camera");
    const summary = result.summary;

    preview.src = result.analysis_url;
    populateIncidentReport(viewer, report);
    location.textContent = result.location;
    camera.textContent = result.camera_id;
    addMetric(metrics, "Duration", formatDuration(summary.duration_seconds));
    addMetric(metrics, "Frames", Number(summary.frame_count).toLocaleString());
    addMetric(metrics, "Temporal clips", String(summary.complete_clips));
    addMetric(metrics, "Peak score", formatScore(summary.score_max));
    addMetric(metrics, "Moments", String(result.frames.length));
    host.append(viewer);
    loadGemmaReport(viewer, result);
  }

  function renderDemoGallery(result) {
    demoHost.replaceChildren();
    const gallery = document.createElement("div");
    gallery.className = "demo-gallery";
    const heading = document.createElement("div");
    heading.className = "demo-gallery-heading";
    heading.innerHTML = "<strong>FEATURED SCENARIOS</strong><span>Select a video to view its analysis</span>";
    const grid = document.createElement("div");
    grid.className = "demo-grid demo-grid-featured";
    const allHeading = document.createElement("div");
    allHeading.className = "demo-gallery-heading demo-gallery-subheading";
    allHeading.innerHTML = "<strong>ALL SCENARIOS</strong><span>10 additional anomaly classes</span>";
    const allGrid = document.createElement("div");
    allGrid.className = "demo-grid";
    const resultHost = document.createElement("div");
    resultHost.className = "demo-result";

    result.demos.forEach((demo, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "demo-card";
      button.setAttribute("aria-pressed", String(index === 0));
      const image = document.createElement("img");
      image.src = demo.thumbnail_url;
      image.alt = `${demo.label} surveillance video thumbnail`;
      const label = document.createElement("span");
      label.textContent = demo.label;
      button.append(image, label);
      button.addEventListener("click", () => {
        gallery.querySelectorAll(".demo-card").forEach((card) => {
          card.classList.remove("is-active");
          card.setAttribute("aria-pressed", "false");
        });
        button.classList.add("is-active");
        button.setAttribute("aria-pressed", "true");
        renderResult(resultHost, demo);
      });
      if (index === 0) button.classList.add("is-active");
      (demo.featured ? grid : allGrid).append(button);
    });

    gallery.append(heading, grid, allHeading, allGrid);
    demoHost.append(gallery, resultHost);
    renderResult(resultHost, result.demos[0]);
  }

  async function loadDemo() {
    try {
      const response = await fetch(app.dataset.demoUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("The demo response could not be loaded.");
      const result = await response.json();
      if (!result.ready) {
        renderEmpty(demoHost);
        return;
      }
      if (result.demos?.length) renderDemoGallery(result);
      else renderResult(demoHost, result);
    } catch (error) {
      renderEmpty(demoHost, error.message);
    }
  }

  function humanSize(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function extensionFor(file) {
    const dot = file.name.lastIndexOf(".");
    return dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  }

  function showError(message) {
    statusHost.replaceChildren();
    const state = document.createElement("div");
    state.className = "error-state";
    const title = document.createElement("strong");
    const copy = document.createElement("p");
    title.textContent = "Analysis unavailable";
    copy.textContent = message;
    state.append(title, copy);
    statusHost.append(state);
  }

  function setFile(file) {
    statusHost.replaceChildren();
    testHost.replaceChildren();
    if (!file) {
      currentFile = null;
      input.value = "";
      selectedFile.hidden = true;
      analyzeButton.disabled = true;
      return;
    }
    if (!allowedExtensions.includes(extensionFor(file))) {
      setFile(null);
      showError("Use an MP4, MOV, AVI, or MKV video.");
      return;
    }
    if (file.size > maxBytes) {
      setFile(null);
      showError("The video exceeds the 100 MB local-demo limit.");
      return;
    }
    if (!file.size) {
      setFile(null);
      showError("The selected video is empty.");
      return;
    }
    currentFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = humanSize(file.size);
    selectedFile.hidden = false;
    analyzeButton.disabled = false;
  }

  input.addEventListener("change", () => setFile(input.files[0]));
  removeFile.addEventListener("click", () => setFile(null));
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  }));
  dropZone.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));

  function startProcessing() {
    statusHost.replaceChildren();
    const state = document.createElement("div");
    state.className = "processing-state";
    const loader = document.createElement("span");
    loader.className = "loader";
    const body = document.createElement("p");
    const title = document.createElement("strong");
    const timer = document.createElement("span");
    title.textContent = "Preparing analysis";
    body.append(title, document.createTextNode("Loading the pre-generated local result · "), timer);
    state.append(loader, body);
    statusHost.append(state);
    const started = Date.now();
    const update = () => { timer.textContent = `${Math.floor((Date.now() - started) / 1000)}s elapsed`; };
    update();
    elapsedTimer = window.setInterval(update, 1000);
  }

  function stopProcessing() {
    if (elapsedTimer) window.clearInterval(elapsedTimer);
    elapsedTimer = null;
  }

  function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentFile) return;
    analyzeButton.disabled = true;
    input.disabled = true;
    removeFile.disabled = true;
    testHost.replaceChildren();
    startProcessing();
    try {
      await wait(7000);
      const response = await fetch(app.dataset.sampleUrl, { headers: { Accept: "application/json" } });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Analysis failed.");
      statusHost.replaceChildren();
      renderResult(testHost, result);
      testHost.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showError(error.message || "Analysis failed. Try again.");
    } finally {
      stopProcessing();
      analyzeButton.disabled = !currentFile;
      input.disabled = false;
      removeFile.disabled = false;
    }
  });

  const requestedTab = new URLSearchParams(window.location.search).get("tab");
  if (requestedTab === "test") activateTab("test", false, false);
  loadDemo();
})();
