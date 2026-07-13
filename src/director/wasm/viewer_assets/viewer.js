// createViewer creates a VTK WASM viewer from backend scene metadata. It imports
// the scene, optionally streams poses, and provides object, property, debug,
// and picking controls.

import { ContextMenu } from "./context-menu.js";
import { DebugPanel } from "./debug-panel.js";
import { GeometryCache } from "./geometry-cache.js";
import { ObjectTreePanel } from "./object-tree-panel.js";
import { PoseStream } from "./pose-stream.js";
import { PropertiesPanel } from "./properties-panel.js";
import { SceneModel } from "./scene-model.js";
import { SceneSession } from "./scene-session.js";

function ensureStylesheet() {
  const href = new URL("./viewer.css", import.meta.url).href;
  if (document.querySelector(`link[href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

/**
 * @param {object} config
 * @param {HTMLElement} config.container          Host element (made the viewer root).
 * @param {string} config.infoUrl                 GET -> {render_window_id, wasm_url, scene_version, objects}.
 * @param {(id:number)=>string} config.statusUrl  Build status endpoint URL.
 * @param {(id:number)=>string} config.stateUrl   Build state endpoint URL.
 * @param {(hash:string)=>string} config.blobUrl  Build blob endpoint URL.
 * @param {string} [config.wsUrl]                  Pose-stream WebSocket URL (omit for static scenes).
 * @param {string} [config.cacheNamespace]         Namespace for the geometry cache.
 * @param {string} [config.remoteModuleUrl]        Override the RemoteSession module URL.
 * @param {{scene?:boolean, debug?:boolean}} [config.panels]
 *     Initial panel visibility; both default to hidden.
 * @param {boolean} [config.contextMenu]           Right-click panel toggles (default true).
 * @returns {Promise<{session, model, tree, props, stream, cache, debug, panels,
 *     setBackground, pickAtEvent}>}
 */
export async function createViewer(config) {
  const { container, infoUrl, statusUrl, stateUrl, blobUrl, wsUrl } = config;
  ensureStylesheet();
  container.classList.add("vtkv-root");

  const cache = new GeometryCache();

  // The debug panel is constructed up front (even when hidden) so its text
  // console captures the whole startup sequence.
  const debug = new DebugPanel(cache);
  debug.setVisible(config.panels?.debug ?? false);
  container.appendChild(debug.el);

  debug.setStatus("Fetching scene info…");
  const info = await (await fetch(infoUrl)).json();
  debug.setSceneInfo({
    sceneVersion: info.scene_version,
    objectCount: (info.objects || []).length,
  });

  const session = new SceneSession({
    remoteModuleUrl: config.remoteModuleUrl,
    cache,
    cacheNamespace: config.cacheNamespace || "scene",
    fetchStateRaw: (id) => fetch(stateUrl(id)).then((r) => r.text()),
    fetchBlobRaw: (hash) =>
      fetch(blobUrl(hash))
        .then((r) => r.arrayBuffer())
        .then((b) => new Uint8Array(b)),
    fetchStatusRaw: (id) => fetch(statusUrl(id)).then((r) => r.json()),
    onStats: (s) => debug.setCache(s),
  });

  debug.setStatus("Loading WASM runtime…");
  await session.load({
    wasmUrl: info.wasm_url,
    renderWindowId: info.render_window_id,
    sceneVersion: info.scene_version,
  });

  debug.setStatus("Importing scene (one-time)…");
  await session.importScene(container);

  // Build the object model + panels from the backend metadata tree.
  const model = new SceneModel(info.objects || []);

  const poseTargets = {};
  for (const node of info.objects || []) {
    if (node.kind === "object") poseTargets[node.key] = node.matrix_id;
  }
  session.setPoseTargets(poseTargets);

  // Apply model edits to the live WASM scene.
  model.on("propertyChanged", (item, name, value) => {
    if (item.isFolder || !item.ids) return;
    if (name === "Visible") session.setVisible(item.ids.actorId, value);
    else if (name === "Color") session.setColor(item.ids.propertyId, value);
    else if (name === "Alpha") session.setOpacity(item.ids.propertyId, value);
    else if (name === "Surface Mode") session.setSurfaceMode(item.ids.propertyId, value);
  });

  const tree = new ObjectTreePanel(model);
  const props = new PropertiesPanel(model);
  container.appendChild(tree.el);
  container.appendChild(props.el);

  // The scene panel toggle covers the object tree and the properties panel
  // together -- properties are meaningless without a tree selection.
  let sceneVisible = false;
  const panels = {
    showScene(visible) {
      sceneVisible = visible;
      tree.el.classList.toggle("vtkv-hidden", !visible);
      props.el.classList.toggle("vtkv-hidden", !visible);
    },
    sceneVisible: () => sceneVisible,
    showDebug: (visible) => debug.setVisible(visible),
    debugVisible: () => debug.visible,
  };
  panels.showScene(config.panels?.scene ?? false);

  // Hardware picking needs the interactor's picker and the renderer, so it is
  // only available when the backend reports both ids in the info payload.
  const pickingAvailable = info.interactor_id != null && info.renderer_id != null;

  /**
   * Hardware-pick the scene object under a pointer event.
   * @param {{clientX:number, clientY:number}} event
   * @returns {{item:SceneItem, position:number[]}|null}
   */
  const pickAtEvent = (event) => {
    if (!pickingAvailable) {
      throw new Error("Backend info payload has no interactor_id/renderer_id; cannot pick");
    }
    // VTK display coordinates: device pixels with origin at the bottom-left,
    // matching the render window size set in SceneSession._observeResize.
    const rect = container.getBoundingClientRect();
    const x = (event.clientX - rect.left) * devicePixelRatio;
    const y = (rect.height - (event.clientY - rect.top)) * devicePixelRatio;
    const hit = session.pick(info.interactor_id, info.renderer_id, x, y);
    if (!hit) return null;
    const item = model.findByActorId(hit.actorId);
    if (!item) return null;
    return { item, position: hit.position };
  };

  if (config.contextMenu !== false) {
    const panelToggleItems = [
      {
        label: "Scene panel",
        isChecked: () => panels.sceneVisible(),
        onToggle: () => panels.showScene(!panels.sceneVisible()),
      },
      {
        label: "Debug info panel",
        isChecked: () => panels.debugVisible(),
        onToggle: () => panels.showDebug(!panels.debugVisible()),
      },
    ];

    new ContextMenu(container, (event) => {
      const items = [];
      if (pickingAvailable) {
        const picked = pickAtEvent(event);
        if (picked) {
          items.push({ header: picked.item.name });
          items.push({
            label: "Select",
            onSelect: () => {
              model.setSelection(picked.item.key);
              // Selection is meaningless while the scene panel is hidden.
              panels.showScene(true);
            },
          });
          items.push({ separator: true });
        }
      }
      items.push(...panelToggleItems);
      return items;
    });
  }

  // Static scenes have no pose stream; everything else still works (tree,
  // properties, caching) because the scene was fully posed at serialization.
  let stream = null;
  if (wsUrl) {
    stream = new PoseStream({
      url: wsUrl,
      onFrame: (poses, seq) => {
        session.applyPoseFrame(poses);
        debug.onPoseFrame(seq);
      },
      onStatus: (msg, isError) => debug.setStatus(msg, isError),
    });
    stream.connect();
  }

  // Renderer-level controls for host pages (e.g. background changes driven
  // from outside an iframe via postMessage). Requires the backend to report
  // renderer_id in the info payload.
  const setBackground = (bottomRgb, topRgb) => {
    if (info.renderer_id == null) {
      throw new Error("Backend info payload has no renderer_id; cannot set background");
    }
    session.setBackground(info.renderer_id, bottomRgb, topRgb);
  };

  debug.setStatus("Ready");
  return { session, model, tree, props, stream, cache, debug, panels, setBackground, pickAtEvent };
}
