// ObjectTreePanel: floating panel rendering a SceneModel as a folder tree.
//
// Mirrors Director's object tree: folders are expand/collapse-able, every node
// has an eye toggle for Visible, and clicking a row selects it (driving the
// properties panel). The panel is a passive view -- all edits go through
// SceneModel, and it re-renders icons/highlight from model events.

const EYE_VISIBLE = "\u25C9"; // ◉
const EYE_HIDDEN = "\u25CB"; // ○
const CARET_OPEN = "\u25BE"; // ▾
const CARET_CLOSED = "\u25B8"; // ▸

export class ObjectTreePanel {
  /** @param {SceneModel} model @param {{title?:string}} [opts] */
  constructor(model, { title = "Scene" } = {}) {
    this.model = model;
    this.el = document.createElement("div");
    this.el.className = "vtkv-panel vtkv-tree-panel";
    this._rows = new Map(); // key -> {row, eye}

    const header = document.createElement("div");
    header.className = "vtkv-panel-title";
    header.textContent = title;
    this.el.appendChild(header);

    const tree = document.createElement("div");
    tree.className = "vtkv-tree";
    this.el.appendChild(tree);
    for (const root of model.roots) this._renderItem(root, tree, 0);

    model.on("selectionChanged", (item) => this._updateSelection(item));
    model.on("propertyChanged", (item, name) => {
      if (name === "Visible") this._updateEye(item);
    });
  }

  _renderItem(item, parentEl, depth) {
    const row = document.createElement("div");
    row.className = "vtkv-tree-row";
    row.style.paddingLeft = `${6 + depth * 14}px`;

    const hasChildren = item.children.length > 0;
    const caret = document.createElement("span");
    caret.className = "vtkv-caret";
    caret.textContent = hasChildren ? CARET_OPEN : "";

    const label = document.createElement("span");
    label.className = item.isFolder ? "vtkv-tree-label folder" : "vtkv-tree-label";
    label.textContent = item.name;

    const eye = document.createElement("span");
    eye.className = "vtkv-eye";
    this._paintEye(eye, item.properties.Visible);

    row.append(caret, label, eye);
    parentEl.appendChild(row);
    this._rows.set(item.key, { row, eye });

    const childrenEl = document.createElement("div");
    childrenEl.className = "vtkv-tree-children";
    parentEl.appendChild(childrenEl);
    for (const child of item.children) this._renderItem(child, childrenEl, depth + 1);

    if (hasChildren) {
      caret.addEventListener("click", (e) => {
        e.stopPropagation();
        const collapsed = childrenEl.style.display === "none";
        childrenEl.style.display = collapsed ? "" : "none";
        caret.textContent = collapsed ? CARET_OPEN : CARET_CLOSED;
      });
    }

    row.addEventListener("click", () => this.model.setSelection(item.key));
    eye.addEventListener("click", (e) => {
      e.stopPropagation();
      this.model.setProperty(item.key, "Visible", !item.properties.Visible);
    });
  }

  _paintEye(eye, visible) {
    eye.textContent = visible ? EYE_VISIBLE : EYE_HIDDEN;
    eye.classList.toggle("hidden", !visible);
  }

  _updateEye(item) {
    const entry = this._rows.get(item.key);
    if (entry) this._paintEye(entry.eye, item.properties.Visible);
  }

  _updateSelection(item) {
    for (const [key, entry] of this._rows) {
      entry.row.classList.toggle("selected", !!item && key === item.key);
    }
  }
}
