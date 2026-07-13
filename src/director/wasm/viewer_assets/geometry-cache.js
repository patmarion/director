// IndexedDB key/value cache for serialized VTK geometry.
//
// RemoteSession imports a scene by fetching per-object JSON "state" and binary
// "blob" payloads. Those are large and stable, so caching them in the browser
// lets a reload skip the network entirely. States are namespaced by the
// backend's `scene_version` (so a server scene-graph change invalidates stale
// states instead of mixing them with fresh ones and rendering black); blobs are
// content-hashed already, so they stay shareable across versions.

const DB_NAME = "vtk-geometry-cache";
const STORE = "kv";

export class GeometryCache {
  constructor(dbName = DB_NAME, storeName = STORE) {
    this._dbName = dbName;
    this._storeName = storeName;
    this._dbPromise = null;
  }

  _open() {
    if (!this._dbPromise) {
      this._dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(this._dbName, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(this._storeName);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return this._dbPromise;
  }

  async get(key) {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const r = db.transaction(this._storeName, "readonly").objectStore(this._storeName).get(key);
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  }

  async put(key, value) {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this._storeName, "readwrite");
      tx.objectStore(this._storeName).put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async clear() {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this._storeName, "readwrite");
      tx.objectStore(this._storeName).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }
}
