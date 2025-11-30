"""Helpers for persisting PropertySet instances via QSettings."""

from __future__ import annotations

import json
from typing import Optional

from qtpy import QtCore

from director.propertyset import PropertySet

from director.frame_properties import FrameProperties
from director.visualization import FrameItem

def _get_settings(settings: Optional[QtCore.QSettings] = None) -> QtCore.QSettings:
    return settings or QtCore.QSettings()


def save_properties_to_settings(properties: PropertySet, key: str, settings: Optional[QtCore.QSettings] = None):
    """Serialize a PropertySet to JSON and store it in QSettings under key."""
    state = properties.get_state_dict()
    serialized = json.dumps(state)
    qsettings = _get_settings(settings)
    qsettings.setValue(key, serialized)
    qsettings.sync()


def restore_properties_from_settings(
    properties: PropertySet,
    key: str,
    merge: bool = True,
    settings: Optional[QtCore.QSettings] = None,
) -> bool:
    """Load JSON data from QSettings and restore it into the provided PropertySet.

    Returns True if state was found and restored.
    """
    qsettings = _get_settings(settings)
    stored = qsettings.value(key, None)
    if stored in (None, ''):
        return False
    if isinstance(stored, QtCore.QByteArray):
        stored = bytes(stored).decode('utf-8')
    state = json.loads(str(stored))
    properties.restore_from_state_dict(state, merge=merge)
    return True


def _filter_state(state, names_to_filter):
    for key in ["properties", "attributes"]:
        items = state[key]
        state[key] = {k: v for k, v in items.items() if k not in names_to_filter}


def save_object_properties(objs, settings_key):
    state_list = []
    for obj in objs:
        obj_path = obj.getObjectTree().getObjectPath(obj)
        prop_state = obj.properties.get_state_dict()
        if isinstance(obj, FrameItem) and not obj.properties.name == "grid":
            _filter_state(prop_state, [FrameProperties.POSITION_PROPERTY, FrameProperties.RPY_PROPERTY])
        state_list.append((obj_path, prop_state))
    serialized = json.dumps(state_list)
    qsettings = _get_settings()
    qsettings.setValue(settings_key, serialized)
    qsettings.sync()


def restore_object_properties(objs, settings_key, merge=True):
    qsettings = _get_settings()
    serialized = qsettings.value(settings_key, None)
    if not serialized:
        return
    state_list = json.loads(serialized)
    path_to_obj = {obj.getObjectTree().getObjectPath(obj): obj for obj in objs}
    for path, prop_state in state_list:
        obj = path_to_obj.get(tuple(path))
        if obj:
            obj.properties.restore_from_state_dict(prop_state, merge=merge)