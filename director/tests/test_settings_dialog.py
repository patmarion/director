import json
from pathlib import Path
import pytest
from qtpy import QtCore, QtWidgets

from director.propertyset import PropertyAttributes, PropertySet
from director.settings_dialog import SettingsDialog


def ensure_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def create_property_sets():
    camera = PropertySet()
    camera.addProperty("Visible", True)
    camera.addProperty(
        "Surface Mode",
        0,
        attributes=PropertyAttributes(enumNames=["Surface", "Wireframe", "Points"]),
    )

    view = PropertySet()
    view.addProperty("Background Color", (0.1, 0.1, 0.1))
    view.addProperty("Alpha", 0.5)
    return camera, view


def test_settings_dialog_save_restore(tmp_path, interactive=False):
    app = ensure_qapp()
    settings_file = tmp_path / "settings.ini"
    qsettings = QtCore.QSettings(str(settings_file), QtCore.QSettings.IniFormat)
    qsettings.clear()

    camera, view = create_property_sets()
    dialog = SettingsDialog("TestDialog", settings=qsettings)
    dialog.add_settings("Camera", camera)
    dialog.add_settings("View", view)

    # Select camera entry and change values
    dialog.list_widget.setCurrentRow(0)
    camera.setProperty("Visible", False)
    camera.setProperty("Surface Mode", "Wireframe")
    dialog.apply_current_settings()

    # Modify again to ensure restore comes from persistence and reset button works
    camera.setProperty("Visible", True)
    camera.setProperty("Surface Mode", "Points")
    dialog.reset_button.click()
    assert camera.getPropertyEnumValue("Surface Mode") == "Wireframe"

    dialog.restore_all()

    assert camera.getProperty("Visible") is False
    assert camera.getProperty("Surface Mode") == 1
    assert camera.getPropertyEnumValue("Surface Mode") == "Wireframe"

    # Test reset for second entry
    dialog.list_widget.setCurrentRow(1)
    view.setProperty("Alpha", 0.9)
    dialog.list_widget.setCurrentRow(0)
    assert dialog.apply_button.isEnabled()
    dialog.reset_button.click()
    dialog.list_widget.setCurrentRow(1)
    dialog.reset_defaults_button.click()
    assert view.getProperty("Alpha") == 0.5

    # Persist selected entry and ensure new dialog restores it
    dialog.list_widget.setCurrentRow(1)
    camera2, view2 = create_property_sets()
    dialog2 = SettingsDialog("TestDialog", settings=qsettings)
    dialog2.add_settings("Camera", camera2)
    dialog2.add_settings("View", view2)
    dialog2.restore_all()
    assert dialog2.list_widget.currentItem().text() == "View"
    assert camera2.getPropertyEnumValue("Surface Mode") == "Wireframe"
    assert camera2.getProperty("Visible") is False

    # Verify settings persisted on disk as JSON
    qsettings.sync()
    stored = qsettings.value("TestDialog/Camera")
    assert stored is not None
    restored_state = json.loads(str(stored))
    assert restored_state["properties"]["Visible"] is False

    # After applying, buttons should deactivate even if selection changes
    dialog.list_widget.setCurrentRow(0)
    camera.setProperty("Visible", True)
    dialog.list_widget.setCurrentRow(1)
    dialog.apply_button.click()
    assert not dialog.apply_button.isEnabled()

    if interactive:
        dialog.show()
        app.exec_()


def interactive_test():
    app = ensure_qapp()
    camera, view = create_property_sets()
    settings_file = "/tmp/interactive_testsettings.ini"
    qsettings = QtCore.QSettings(settings_file, QtCore.QSettings.IniFormat)
    dialog = SettingsDialog("TestDialog", settings=qsettings)
    dialog.add_settings("Camera", camera)
    dialog.add_settings("View", view)
    dialog.restore_all()
    dialog.show()
    app.exec_()


if __name__ == "__main__":
    interactive_test()
