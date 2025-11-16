"""Dialog for browsing and editing application settings stored as PropertySets."""

from __future__ import annotations

import copy
from typing import Dict, Optional

from qtpy import QtCore, QtGui, QtWidgets

from director.propertiespanel import PropertiesPanel
from director.settings_helper import (
    restore_properties_from_settings,
    save_properties_to_settings,
)


class SettingsDialog(QtWidgets.QDialog):
    """Non-modal dialog that hosts multiple PropertySet editors."""

    def __init__(
        self,
        dialog_name: str,
        parent: Optional[QtWidgets.QWidget] = None,
        settings: Optional[QtCore.QSettings] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(dialog_name)
        self.setModal(False)

        self._dialog_name = dialog_name
        self._qsettings = settings or QtCore.QSettings()
        self._entries: Dict[str, Dict[str, object]] = {}
        self._stored_selection_name = self._qsettings.value(
            f"{self._dialog_name}/_selected_name", None
        )
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_settings(self, name: str, property_set):
        """Register a PropertySet with a display name."""
        if name in self._entries:
            raise ValueError(f"Settings '{name}' already added.")

        default_state = property_set.get_state_dict()
        self._entries[name] = {
            "properties": property_set,
            "default_state": copy.deepcopy(default_state),
            "last_saved": copy.deepcopy(default_state),
        }

        item = QtWidgets.QListWidgetItem(name)
        self.list_widget.addItem(item)

        if self.list_widget.count() == 1 and self.list_widget.currentRow() == -1:
            self.list_widget.setCurrentRow(0)
        self._apply_stored_selection()

    def apply_current_settings(self):
        entry = self._current_entry()
        if not entry:
            return
        name = self._current_name()
        save_properties_to_settings(
            entry["properties"],
            self._storage_key(name),
            settings=self._qsettings,
        )
        entry["last_saved"] = entry["properties"].get_state_dict()
        self._store_selected_name(name)
        self._update_button_states()

    def reset_current_settings(self):
        entry = self._current_entry()
        if not entry:
            return

        if self.sender() is self.reset_defaults_button:
            state_copy = copy.deepcopy(entry["default_state"])
        else:
            state_copy = copy.deepcopy(entry["last_saved"])
        entry["properties"].restore_from_state_dict(state_copy, merge=True)
        self._update_button_states()

    def restore_all(self):
        """Restore settings for all registered PropertySets from QSettings."""
        for name, entry in self._entries.items():
            restore_properties_from_settings(
                entry["properties"],
                self._storage_key(name),
                merge=True,
                settings=self._qsettings,
            )
            entry["last_saved"] = entry["properties"].get_state_dict()
        self._apply_stored_selection()
        self._update_button_states()

    def restore_persistent_settings(self):
        """Compatibility alias for restore_all()."""
        self.restore_all()

    # ------------------------------------------------------------------
    # UI setup and interactions
    # ------------------------------------------------------------------

    def _build_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        main_layout.addWidget(self.list_widget, 1)

        right_container = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(right_container, 2)

        self.properties_panel = PropertiesPanel(right_container)
        self.properties_panel.hide_header(True)
        right_layout.addWidget(self.properties_panel, 1)

        button_row = QtWidgets.QHBoxLayout()
        self.reset_defaults_button = QtWidgets.QPushButton("Reset to Defaults")
        self.reset_defaults_button.clicked.connect(self.reset_current_settings)
        button_row.addWidget(self.reset_defaults_button)
        button_row.addStretch()

        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_current_settings)
        button_row.addWidget(self.reset_button)

        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_current_settings)
        button_row.addWidget(self.apply_button)
        right_layout.addLayout(button_row)

    def _on_selection_changed(self, current, _previous):
        name = current.text() if current else None
        if not name or name not in self._entries:
            self.properties_panel.clear()
            self._update_button_states()
            return
        entry = self._entries[name]
        self.properties_panel.connectProperties(entry["properties"])
        self._install_property_changed_hook(entry["properties"])
        self._store_selected_name(name)
        self._update_button_states()

    def _storage_key(self, settings_name: str) -> str:
        return f"{self._dialog_name}/{settings_name}"

    def _current_name(self) -> Optional[str]:
        item = self.list_widget.currentItem()
        return item.text() if item else None

    def _current_entry(self):
        name = self._current_name()
        if not name:
            return None
        return self._entries.get(name)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _install_property_changed_hook(self, property_set):
        if hasattr(self, "_property_changed_hook_id"):
            property_set.disconnectPropertyChanged(self._property_changed_hook_id)
        self._property_changed_hook_id = property_set.connectPropertyChanged(
            lambda *_: self._update_button_states()
        )

    def _has_changes(self, name: str) -> bool:
        entry = self._entries[name]
        current_state = entry["properties"].get_state_dict()
        return current_state != entry["last_saved"]

    def _update_button_states(self):
        name = self._current_name()
        has_changes = bool(name and self._has_changes(name))

        def set_button_style(button: QtWidgets.QPushButton, enabled: bool, color: QtGui.QColor):
            button.setEnabled(enabled)
            palette = button.palette()
            default_palette = QtWidgets.QPushButton().palette()
            if enabled:
                palette.setColor(QtGui.QPalette.Button, color)
                palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
            else:
                palette = default_palette
            button.setPalette(palette)

        set_button_style(self.reset_button, has_changes, QtGui.QColor("#1e88e5"))  # blue
        set_button_style(self.apply_button, has_changes, QtGui.QColor("#2e7d32"))  # green

    def _store_selected_name(self, name: Optional[str] = None):
        current_name = name or self._current_name()
        if current_name:
            self._stored_selection_name = current_name
            self._qsettings.setValue(f"{self._dialog_name}/_selected_name", current_name)

    def _apply_stored_selection(self):
        if not self._stored_selection_name:
            return
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.text() == self._stored_selection_name:
                self.list_widget.setCurrentItem(item)
                self._stored_selection_name = None
                return

