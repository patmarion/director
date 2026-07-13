// PropertiesPanel: floating panel showing the selected item's editable
// properties, analogous to Director's property panel.
//
// It renders one editor per property based on its attribute `type`
// (string -> read-only text, bool -> checkbox, color -> color swatch,
// number -> range slider, enum -> select). Edits flow into
// SceneModel.setProperty; the panel also listens for propertyChanged so
// cascaded/external edits stay in sync.

export class PropertiesPanel {
  /** @param {SceneModel} model @param {{title?:string}} [opts] */
  constructor(model, { title = "Properties" } = {}) {
    this.model = model;
    this.el = document.createElement("div");
    this.el.className = "vtkv-panel vtkv-props-panel";

    const header = document.createElement("div");
    header.className = "vtkv-panel-title";
    header.textContent = title;
    this.el.appendChild(header);

    this._body = document.createElement("div");
    this._body.className = "vtkv-props";
    this.el.appendChild(this._body);

    this._editors = new Map(); // prop name -> sync(value)

    model.on("selectionChanged", (item) => this._render(item));
    model.on("propertyChanged", (item, name, value) => {
      if (item === this.model.getSelected()) this._sync(name, value);
    });

    this._render(model.getSelected());
  }

  _render(item) {
    this._body.innerHTML = "";
    this._editors.clear();

    if (!item) {
      const empty = document.createElement("div");
      empty.className = "vtkv-props-empty";
      empty.textContent = "No selection";
      this._body.appendChild(empty);
      return;
    }

    // Show object type as a non-editable hint above the property rows.
    if (item.objectType) {
      const typeRow = this._row("Type");
      const value = document.createElement("span");
      value.className = "vtkv-prop-value";
      value.textContent = item.objectType;
      typeRow.appendChild(value);
      this._body.appendChild(typeRow);
    }

    for (const name of Object.keys(item.properties)) {
      const attr = item.attributes[name] || {};
      this._body.appendChild(this._editorRow(item, name, attr));
    }
  }

  _row(label) {
    const row = document.createElement("div");
    row.className = "vtkv-prop-row";
    const lbl = document.createElement("span");
    lbl.className = "vtkv-prop-label";
    lbl.textContent = label;
    row.appendChild(lbl);
    return row;
  }

  _editorRow(item, name, attr) {
    const row = this._row(name);
    const value = item.properties[name];

    if (attr.type === "string" || attr.readOnly) {
      const span = document.createElement("span");
      span.className = "vtkv-prop-value";
      span.textContent = String(value);
      row.appendChild(span);
      this._editors.set(name, (v) => (span.textContent = String(v)));
    } else if (attr.type === "bool") {
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!value;
      input.addEventListener("change", () =>
        this.model.setProperty(item.key, name, input.checked),
      );
      row.appendChild(input);
      this._editors.set(name, (v) => (input.checked = !!v));
    } else if (attr.type === "color") {
      const input = document.createElement("input");
      input.type = "color";
      input.value = rgbToHex(value);
      input.addEventListener("input", () =>
        this.model.setProperty(item.key, name, hexToRgb(input.value)),
      );
      row.appendChild(input);
      this._editors.set(name, (v) => (input.value = rgbToHex(v)));
    } else if (attr.type === "number") {
      const input = document.createElement("input");
      input.type = "range";
      input.min = attr.min ?? 0;
      input.max = attr.max ?? 1;
      input.step = attr.step ?? 0.01;
      input.value = value;
      input.addEventListener("input", () =>
        this.model.setProperty(item.key, name, parseFloat(input.value)),
      );
      row.appendChild(input);
      this._editors.set(name, (v) => (input.value = v));
    } else if (attr.type === "enum") {
      const select = document.createElement("select");
      for (const option of attr.values || []) {
        const el = document.createElement("option");
        el.value = option;
        el.textContent = option;
        select.appendChild(el);
      }
      select.value = value;
      select.addEventListener("change", () =>
        this.model.setProperty(item.key, name, select.value),
      );
      row.appendChild(select);
      this._editors.set(name, (v) => (select.value = v));
    } else {
      const span = document.createElement("span");
      span.className = "vtkv-prop-value";
      span.textContent = String(value);
      row.appendChild(span);
    }
    return row;
  }

  _sync(name, value) {
    const editor = this._editors.get(name);
    if (editor) editor(value);
  }
}

function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}

function rgbToHex(rgb) {
  const h = (x) =>
    Math.round(clamp01(x) * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${h(rgb[0])}${h(rgb[1])}${h(rgb[2])}`;
}

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}
