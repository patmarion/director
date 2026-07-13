// DebugPanel: floating "Debug Info" panel with live viewer diagnostics.
//
// Shows the current status line, scene facts (version + object count), the
// geometry cache hit/miss summary with a clear-cache button, pose-stream frame
// counters, and a small text console recording timestamped info/error
// messages. The panel is always constructed even when hidden so the console
// captures the full startup sequence; visibility is a pure CSS toggle.

const MAX_CONSOLE_LINES = 200;
// Pose frames arrive at robot rate (~30 Hz); repaint the counters at a low
// rate so the panel itself never becomes render overhead.
const POSE_PAINT_INTERVAL_MS = 500;

export class DebugPanel {
  /** @param {GeometryCache} cache @param {{title?:string}} [opts] */
  constructor(cache, { title = "Debug Info" } = {}) {
    this.el = document.createElement("div");
    this.el.className = "vtkv-panel vtkv-debug";

    const header = document.createElement("div");
    header.className = "vtkv-panel-title";
    header.textContent = title;

    const body = document.createElement("div");
    body.className = "vtkv-debug-body";

    this._statusValue = this._appendRow(body, "Status", "Initializing…");
    this._sceneValue = this._appendRow(body, "Scene", "–");
    this._cacheValue = this._appendRow(body, "Geometry", "–");
    this._poseValue = this._appendRow(body, "Poses", "no frames");

    const buttons = document.createElement("div");
    buttons.className = "vtkv-buttons";
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "Clear geometry cache";
    clearBtn.addEventListener("click", async () => {
      await cache.clear();
      this._cacheValue.textContent = "cache cleared — reload to refetch";
      this._cacheValue.className = "vtkv-debug-value";
      this.log("Geometry cache cleared");
    });
    buttons.appendChild(clearBtn);
    body.appendChild(buttons);

    this._console = document.createElement("div");
    this._console.className = "vtkv-console";

    this.el.append(header, body, this._console);

    this._frameCount = 0;
    this._paintedFrameCount = 0;
    this._lastPosePaintMs = 0;
  }

  /** Update the status row; every status change is also logged to the console. */
  setStatus(msg, isError = false) {
    this._statusValue.textContent = msg;
    this._statusValue.className = isError ? "vtkv-debug-value error" : "vtkv-debug-value";
    this.log(msg, isError ? "error" : "info");
  }

  /** Append a timestamped line to the text console (ring-buffered). */
  log(msg, level = "info") {
    const line = document.createElement("div");
    line.className = `vtkv-console-line ${level}`;
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    line.textContent = `[${hh}:${mm}:${ss}] ${msg}`;
    this._console.appendChild(line);
    while (this._console.childElementCount > MAX_CONSOLE_LINES) {
      this._console.firstElementChild.remove();
    }
    this._console.scrollTop = this._console.scrollHeight;
  }

  setSceneInfo({ sceneVersion, objectCount }) {
    this._sceneValue.textContent = `${objectCount} objects · version ${sceneVersion}`;
    this.log(`Scene info: ${objectCount} objects, version ${sceneVersion}`);
  }

  setCache(stats) {
    const net = stats.stateNet + stats.blobNet;
    const hit = stats.stateHit + stats.blobHit;
    let source = "mixed";
    let cls = "vtkv-debug-value accent";
    if (net === 0 && hit > 0) source = "cache";
    else if (hit === 0 && net > 0) {
      source = "network";
      cls = "vtkv-debug-value network";
    }
    this._cacheValue.className = cls;
    this._cacheValue.textContent =
      `${source} — states ${stats.stateHit}/${stats.stateNet} · ` +
      `blobs ${stats.blobHit}/${stats.blobNet} (cache/net)`;
  }

  /** Called per pose frame; DOM updates are throttled to stay off the hot path. */
  onPoseFrame(seq) {
    this._frameCount++;
    const now = performance.now();
    if (now - this._lastPosePaintMs < POSE_PAINT_INTERVAL_MS) return;
    const elapsedS = (now - this._lastPosePaintMs) / 1000;
    const rateHz = (this._frameCount - this._paintedFrameCount) / elapsedS;
    this._lastPosePaintMs = now;
    this._paintedFrameCount = this._frameCount;
    this._poseValue.textContent =
      `${this._frameCount} frames · seq ${seq} · ${rateHz.toFixed(1)} Hz`;
  }

  setVisible(visible) {
    this.el.classList.toggle("vtkv-hidden", !visible);
  }

  get visible() {
    return !this.el.classList.contains("vtkv-hidden");
  }

  _appendRow(parent, label, initialValue) {
    const row = document.createElement("div");
    row.className = "vtkv-debug-row";
    const lbl = document.createElement("span");
    lbl.className = "vtkv-debug-label";
    lbl.textContent = label;
    const value = document.createElement("span");
    value.className = "vtkv-debug-value";
    value.textContent = initialValue;
    row.append(lbl, value);
    parent.appendChild(row);
    return value;
  }
}
