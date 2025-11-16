"""Helpers for persisting PropertySet instances via QSettings."""

from __future__ import annotations

import json
from typing import Optional

from qtpy import QtCore

from director.propertyset import PropertySet


def _get_settings(settings: Optional[QtCore.QSettings]) -> QtCore.QSettings:
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

