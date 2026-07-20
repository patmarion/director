// SceneSession manages a VTK WASM RemoteSession for a browser viewer.
//
// It imports the scene once, then updates existing objects for live motion and
// property edits before rendering the view.
//
// VTK 9.x serialization uses these fields:
//   - pose      -> the actor's UserMatrix (a vtkMatrix4x4) "Data" (row-major 16)
//   - visibility-> the actor's "Visibility" (0/1)
//   - color     -> the property's Color/Ambient/Diffuse/Specular channels
//   - opacity   -> the property's "Opacity"
//   - surface   -> the property's "Representation" (1=wireframe, 2=surface)
//                  and "EdgeVisibility" (0/1)

const DEFAULT_REMOTE_URL = "https://unpkg.com/@kitware/vtk-wasm@1.6.0/dist/esm/remote.mjs";

export class SceneSession {
  /**
   * @param {object} cfg
   * @param {string} [cfg.remoteModuleUrl] URL of the RemoteSession ESM module.
   * @param {GeometryCache} cfg.cache      IndexedDB cache instance.
   * @param {string} cfg.cacheNamespace    Namespace for state cache keys (e.g. model id).
   * @param {(id:number)=>Promise<string>} cfg.fetchStateRaw       Fetch JSON state text.
   * @param {(hash:string)=>Promise<Uint8Array>} cfg.fetchBlobRaw  Fetch binary blob.
   * @param {(id:number)=>Promise<object>} cfg.fetchStatusRaw      Fetch dependency status.
   * @param {(stats:object)=>void} [cfg.onStats]                   Cache-stats callback.
   */
  constructor(cfg) {
    this._remoteModuleUrl = cfg.remoteModuleUrl || DEFAULT_REMOTE_URL;
    this._cache = cfg.cache;
    this._cacheNamespace = cfg.cacheNamespace || "scene";
    this._fetchStateRaw = cfg.fetchStateRaw;
    this._fetchBlobRaw = cfg.fetchBlobRaw;
    this._fetchStatusRaw = cfg.fetchStatusRaw;
    this._onStats = cfg.onStats || (() => {});

    this.session = null;
    this.renderWindowId = null;
    this.sceneVersion = "v0";
    this._poseTargets = {}; // object key -> matrix id
    this._propPickerId = null; // resolved lazily from the interactor
    this.stats = { stateHit: 0, stateNet: 0, blobHit: 0, blobNet: 0 };
  }

  /**
   * Verify the WASM runtime is actually being served before handing the URL
   * to RemoteSession.load, which swallows fetch failures and only errors much
   * later with a misleading "WASM module is not loaded yet". The probe also
   * triggers the server's lazy runtime download, so its 503 body (e.g.
   * "download from Kitware failed") is the real cause and worth surfacing.
   */
  async _assertRuntimeAvailable(wasmUrl) {
    // New VTK naming first, then the pre-9.5.20250531 legacy naming.
    for (const name of ["vtkWebAssembly.mjs", "vtkWasmSceneManager.mjs"]) {
      const resp = await fetch(`${wasmUrl}/${name}`, { method: "HEAD" });
      if (resp.ok) return;
      if (resp.status !== 404) {
        // The server's error body (e.g. "download from Kitware failed") is
        // the real cause, so prefer it over a generic message.
        const body = await fetch(`${wasmUrl}/${name}`);
        const detail = await body.text();
        throw new Error(detail || `VTK WASM runtime request failed: HTTP ${body.status}`);
      }
    }
    throw new Error(`VTK WASM runtime not available: no runtime files at ${wasmUrl}`);
  }

  /** Import the RemoteSession module, bind cache-aware network, load the WASM. */
  async load({ wasmUrl, renderWindowId, sceneVersion }) {
    this.renderWindowId = renderWindowId;
    this.sceneVersion = sceneVersion || "v0";

    await this._assertRuntimeAvailable(wasmUrl);
    const mod = await import(this._remoteModuleUrl);
    const RemoteSession = mod.RemoteSession;
    this.session = new RemoteSession();
    this.session.bindNetwork(
      (id) => this._fetchState(id),
      (hash) => this._fetchBlob(hash),
      (id) => this._fetchStatusRaw(id),
    );
    await this.session.load(wasmUrl);
  }

  /** Bind the render window to a DOM container and import the scene once. */
  async importScene(container) {
    const rwId = this.renderWindowId;
    this.session.bindCanvasToDOM(rwId, container);

    const canvas = container.querySelector(this.session.getCanvasSelector(rwId));
    if (canvas) {
      canvas.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%";
      canvas.addEventListener("contextmenu", (e) => e.preventDefault());
      canvas.addEventListener("pointerdown", (e) => canvas.setPointerCapture(e.pointerId));
    }

    await this.session.update(rwId, true);
    this.session.sceneManager.startEventLoop(rwId);
    this._onStats(this.stats);
    this._observeResize(container);
  }

  /** Map of object key -> UserMatrix id, used by applyPoseFrame. */
  setPoseTargets(keyToMatrixId) {
    this._poseTargets = keyToMatrixId || {};
  }

  /**
   * Apply a frame of poses: one set() per moved object, then a single render().
   * @param {Record<string, number[]>} poses object key -> 16 row-major floats
   */
  applyPoseFrame(poses) {
    if (!this.session) return;
    const sm = this.session.sceneManager;
    for (const key in poses) {
      const matrixId = this._poseTargets[key];
      if (matrixId != null) sm.set(matrixId, { Data: poses[key] });
    }
    sm.render(this.renderWindowId);
  }

  setVisible(actorId, visible) {
    this.session.sceneManager.set(actorId, { Visibility: visible ? 1 : 0 });
    this.render();
  }

  setColor(propertyId, rgb) {
    // vtkProperty applies each color channel's setter independently, so set all
    // of them to mirror SetColor (DiffuseColor is what actually renders here).
    this.session.sceneManager.set(propertyId, {
      Color: rgb,
      AmbientColor: rgb,
      DiffuseColor: rgb,
      SpecularColor: rgb,
    });
    this.render();
  }

  setOpacity(propertyId, alpha) {
    this.session.sceneManager.set(propertyId, { Opacity: alpha });
    this.render();
  }

  /**
   * Set how the surface renders, mirroring Director's "Surface Mode" property
   * (visualization.py PolyDataItem).
   * @param {number} propertyId
   * @param {"Surface"|"Wireframe"|"Surface with edges"} mode
   */
  setSurfaceMode(propertyId, mode) {
    const fields = {
      Surface: { Representation: 2, EdgeVisibility: 0 },
      Wireframe: { Representation: 1, EdgeVisibility: 0 },
      "Surface with edges": { Representation: 2, EdgeVisibility: 1 },
    }[mode];
    if (!fields) throw new Error(`Unknown surface mode: ${mode}`);
    this.session.sceneManager.set(propertyId, fields);
    this.render();
  }

  /** Set the ambient light contribution used for hover highlighting. */
  setAmbient(propertyId, ambient) {
    this.session.sceneManager.set(propertyId, { Ambient: ambient });
    this.render();
  }

  /** Exclude/include an actor in hardware picks (vtkProp::Pickable). Useful
   *  for background geometry like ground planes that would otherwise swallow
   *  picks. No render: pickability has no visual effect. */
  setPickable(actorId, pickable) {
    this.session.sceneManager.set(actorId, { Pickable: pickable ? 1 : 0 });
  }

  /**
   * Hardware-pick the front-most prop at a display position.
   *
   * The WASM runtime uses the interactor's vtkPropPicker to perform the
   * selection render.
   *
   * @param {number} interactorId From the backend info payload.
   * @param {number} rendererId   From the backend info payload.
   * @param {number} displayX     Device pixels, origin bottom-left (VTK display coords).
   * @param {number} displayY
   * @returns {{actorId:number, position:number[]}|null} picked actor's WASM id
   *     and the world-space pick position, or null when nothing was hit.
   */
  pick(interactorId, rendererId, displayX, displayY) {
    const sm = this.session.sceneManager;
    if (this._propPickerId == null) {
      this._propPickerId = sm.invoke(interactorId, "GetPicker", []).Id;
    }
    const hit = sm.invoke(this._propPickerId, "PickProp", [displayX, displayY, { Id: rendererId }]);
    if (!hit) return null;
    const prop = sm.invoke(this._propPickerId, "GetViewProp", []);
    if (!prop || prop.Id == null) return null;
    const position = sm.invoke(this._propPickerId, "GetPickPosition", []);
    return { actorId: prop.Id, position };
  }

  /**
   * Set the renderer's gradient background. In VTK's gradient mode,
   * `Background` is the bottom color and `Background2` the top.
   * @param {number} rendererId  From the backend info payload.
   * @param {number[]} bottomRgb @param {number[]} topRgb  0..1 channels.
   */
  setBackground(rendererId, bottomRgb, topRgb) {
    this.session.sceneManager.set(rendererId, {
      Background: bottomRgb,
      Background2: topRgb || bottomRgb,
    });
    this.render();
  }

  render() {
    if (this.session) this.session.sceneManager.render(this.renderWindowId);
  }

  // ── cache-aware fetchers passed to RemoteSession.bindNetwork ────────

  async _fetchState(id) {
    const key = `${this._cacheNamespace}:${this.sceneVersion}:state:${id}`;
    const cached = await this._cache.get(key);
    if (cached != null) {
      this.stats.stateHit++;
      this._onStats(this.stats);
      return cached;
    }
    const value = await this._fetchStateRaw(id);
    await this._cache.put(key, value);
    this.stats.stateNet++;
    this._onStats(this.stats);
    return value;
  }

  async _fetchBlob(hash) {
    const key = `blob:${hash}`;
    const cached = await this._cache.get(key);
    if (cached != null) {
      this.stats.blobHit++;
      this._onStats(this.stats);
      return cached instanceof Uint8Array ? cached : new Uint8Array(cached);
    }
    const value = await this._fetchBlobRaw(hash);
    await this._cache.put(key, value);
    this.stats.blobNet++;
    this._onStats(this.stats);
    return value;
  }

  _observeResize(container) {
    new ResizeObserver(() => {
      const { width, height } = container.getBoundingClientRect();
      this.session.setSize(
        this.renderWindowId,
        Math.floor(width * devicePixelRatio + 0.5),
        Math.floor(height * devicePixelRatio + 0.5),
      );
    }).observe(container);
  }
}
