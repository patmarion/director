// SceneModel: a simplified, framework-agnostic analog of Director's
// objectmodel.py + propertyset.py.
//
// The backend ships a flat list of node metadata (folders + objects). This
// builds an in-memory tree where each node owns a small property bag (Name,
// Visible, and for objects Color/Alpha/Surface Mode) with per-property
// attributes (type, readOnly, range, enum values). Panels render the model and
// edit it through setProperty; the model emits events so the 3D session and
// other panels stay in sync. Folder Visible cascades to descendants, like
// Director's ContainerItem.

class Emitter {
  constructor() {
    this._listeners = {};
  }

  on(event, fn) {
    (this._listeners[event] ||= new Set()).add(fn);
    return () => this._listeners[event]?.delete(fn);
  }

  emit(event, ...args) {
    this._listeners[event]?.forEach((fn) => fn(...args));
  }
}

export class SceneItem {
  constructor({ key, name, kind, parentKey, objectType, ids, properties, attributes }) {
    this.key = key;
    this.name = name;
    this.kind = kind; // "folder" | "object"
    this.parentKey = parentKey;
    this.objectType = objectType;
    this.ids = ids; // {actorId, matrixId, propertyId} for objects, else null
    this.properties = properties; // {Name, Visible, Color?, Alpha?, "Surface Mode"?}
    this.attributes = attributes; // {prop: {type, readOnly?, min?, max?, step?, values?}}
    this.children = [];
  }

  get isFolder() {
    return this.kind === "folder";
  }
}

export class SceneModel extends Emitter {
  /** @param {Array<object>} metadata flat node list from the backend /info. */
  constructor(metadata) {
    super();
    this.items = new Map();
    this.roots = [];
    this.selectedKey = null;
    this._build(metadata || []);
  }

  _build(metadata) {
    for (const node of metadata) {
      const isFolder = node.kind === "folder";
      const properties = { Name: node.name, Visible: true };
      const attributes = {
        Name: { type: "string", readOnly: true },
        Visible: { type: "bool" },
      };
      if (!isFolder) {
        properties.Color = node.color || [0.8, 0.8, 0.8];
        properties.Alpha = node.opacity != null ? node.opacity : 1;
        // Scenes serialize as plain surfaces (WasmScene.add_object), so the
        // initial mode is always Surface. Same names as Director's panel.
        properties["Surface Mode"] = "Surface";
        attributes.Color = { type: "color" };
        attributes.Alpha = { type: "number", min: 0, max: 1, step: 0.05 };
        attributes["Surface Mode"] = {
          type: "enum",
          values: ["Surface", "Wireframe", "Surface with edges"],
        };
      }
      this.items.set(
        node.key,
        new SceneItem({
          key: node.key,
          name: node.name,
          kind: node.kind,
          parentKey: node.parent || null,
          objectType: node.object_type || null,
          ids: isFolder
            ? null
            : { actorId: node.actor_id, matrixId: node.matrix_id, propertyId: node.property_id },
          properties,
          attributes,
        }),
      );
    }

    for (const item of this.items.values()) {
      if (item.parentKey && this.items.has(item.parentKey)) {
        this.items.get(item.parentKey).children.push(item);
      } else {
        this.roots.push(item);
      }
    }
  }

  getItem(key) {
    return this.items.get(key) || null;
  }

  /** Resolve a WASM actor id (e.g. from a hardware pick) to its scene item. */
  findByActorId(actorId) {
    for (const item of this.items.values()) {
      if (item.ids && item.ids.actorId === actorId) return item;
    }
    return null;
  }

  getSelected() {
    return this.selectedKey ? this.getItem(this.selectedKey) : null;
  }

  setSelection(key) {
    if (this.selectedKey === key) return;
    this.selectedKey = key;
    this.emit("selectionChanged", this.getItem(key));
  }

  /** Set a property and emit `propertyChanged`; folder Visible cascades down. */
  setProperty(key, name, value) {
    const item = this.getItem(key);
    if (!item) return;
    const attr = item.attributes[name];
    if (attr?.readOnly) return;
    if (_equal(item.properties[name], value)) return;

    item.properties[name] = value;
    this.emit("propertyChanged", item, name, value);

    if (name === "Visible" && item.isFolder) {
      for (const child of item.children) this.setProperty(child.key, "Visible", value);
    }
  }

  /** Iterate all renderable object items (depth-first), for initial sync. */
  *objects() {
    for (const item of this.items.values()) {
      if (!item.isFolder) yield item;
    }
  }
}

function _equal(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => v === b[i]);
  }
  return a === b;
}
