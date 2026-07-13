// ContextMenu: right-click menu with headers, actions, and checkable toggles.
//
// The viewer hides floating panels by default. The menu provides controls for
// those panels and can include the object under the cursor. Items are produced
// each time the menu opens so they reflect the current scene state. Supported
// item shapes:
//
//   {header: string}                          bold non-clickable title row
//   {separator: true}                         thin divider
//   {label, onSelect}                         plain action
//   {label, isChecked, onToggle}              checkable toggle
//
// The menu opens on right-button release only when the pointer has not moved,
// so right-drag camera controls do not open it. The browser's context menu is
// disabled within the viewer.

const DRAG_TOLERANCE_PX = 5;

export class ContextMenu {
  /**
   * @param {HTMLElement} container Viewer root; the menu opens on right-click within it.
   * @param {(event:PointerEvent)=>Array<object>} getItems Called on each open
   *     with the triggering pointer event; return [] to suppress the menu.
   */
  constructor(container, getItems) {
    this._container = container;
    this._getItems = getItems;
    this._rightDownPos = null;

    this.el = document.createElement("div");
    this.el.className = "vtkv-menu vtkv-hidden";
    container.appendChild(this.el);

    container.addEventListener("contextmenu", (event) => event.preventDefault());

    container.addEventListener("pointerdown", (event) => {
      if (this.el.contains(event.target)) return;
      if (event.button === 2) {
        this._rightDownPos = { x: event.clientX, y: event.clientY };
      } else {
        this.close();
      }
    });

    container.addEventListener("pointerup", (event) => {
      if (event.button !== 2 || !this._rightDownPos) return;
      const moved = Math.hypot(
        event.clientX - this._rightDownPos.x,
        event.clientY - this._rightDownPos.y,
      );
      this._rightDownPos = null;
      if (moved <= DRAG_TOLERANCE_PX) this._openAt(event);
    });

    // Clicks outside the viewer and Escape also dismiss the menu.
    document.addEventListener("click", () => this.close());
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") this.close();
    });
  }

  close() {
    this.el.classList.add("vtkv-hidden");
  }

  _openAt(event) {
    const items = this._getItems(event);
    if (!items.length) return;

    this.el.innerHTML = "";
    for (const item of items) {
      this.el.appendChild(this._buildRow(item));
    }

    // Position at the pointer, nudged to stay inside the viewer.
    const bounds = this._container.getBoundingClientRect();
    this.el.classList.remove("vtkv-hidden");
    const menuWidth = this.el.offsetWidth;
    const menuHeight = this.el.offsetHeight;
    let x = event.clientX - bounds.left;
    let y = event.clientY - bounds.top;
    x = Math.min(x, bounds.width - menuWidth - 4);
    y = Math.min(y, bounds.height - menuHeight - 4);
    this.el.style.left = `${Math.max(0, x)}px`;
    this.el.style.top = `${Math.max(0, y)}px`;
  }

  _buildRow(item) {
    if (item.separator) {
      const sep = document.createElement("div");
      sep.className = "vtkv-menu-sep";
      return sep;
    }

    if (item.header) {
      const header = document.createElement("div");
      header.className = "vtkv-menu-header";
      header.textContent = item.header;
      return header;
    }

    const row = document.createElement("div");
    row.className = "vtkv-menu-item";

    const check = document.createElement("span");
    check.className = "vtkv-menu-check";
    check.textContent = item.isChecked && item.isChecked() ? "\u2713" : "";

    const label = document.createElement("span");
    label.textContent = item.label;

    row.append(check, label);
    row.addEventListener("click", (clickEvent) => {
      clickEvent.stopPropagation();
      (item.onToggle || item.onSelect)();
      this.close();
    });
    return row;
  }
}
