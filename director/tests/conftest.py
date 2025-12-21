"""Pytest configuration and shared fixtures for Director tests."""

import sys
import pytest
from qtpy.QtWidgets import QApplication

import faulthandler

import gc
import traceback


import pytest
from unittest.mock import patch
import _pytest.unraisableexception


@pytest.fixture(autouse=True, scope="session")
def disable_gc_collect_harder():
    with patch("_pytest.unraisableexception.gc_collect_harder", return_value=None):
        yield


def _qt_obj_summary(o):
    try:
        mo = o.metaObject()
        cls = mo.className() if mo else type(o).__name__
        name = o.objectName() if hasattr(o, "objectName") else ""
        parent = o.parent()
        parent_desc = None
        if parent is not None:
            pmo = parent.metaObject()
            parent_desc = f"{pmo.className() if pmo else type(parent).__name__}({parent.objectName()})"
        thr = o.thread()
        thr_name = thr.objectName() if thr is not None and hasattr(thr, "objectName") else ""
        return cls, name, parent_desc, thr_name
    except Exception:
        return type(o).__name__, "<?>", None, ""


def dump_live_qt_wrappers(limit=2000):
    from qtpy import QtCore, QtWidgets  # adjust if using PySide2

    QtCore.QObject  # ensure import

    qobjs = []
    timers = []
    widgets = []

    for o in gc.get_objects():
        # isinstance checks can occasionally raise if wrappers are half-dead; guard it.
        try:
            if isinstance(o, QtCore.QObject):
                qobjs.append(o)
                if isinstance(o, QtCore.QTimer):
                    timers.append(o)
                if isinstance(o, QtWidgets.QWidget):
                    widgets.append(o)
        except Exception:
            pass

    print(f"[qt] Live QObject wrappers: {len(qobjs)} | QWidget: {len(widgets)} | QTimer: {len(timers)}")

    active = []
    for t in timers:
        try:
            if t.isActive():
                cls, name, parent_desc, thr_name = _qt_obj_summary(t)
                active.append((t, cls, name, parent_desc, thr_name, t.interval()))
        except Exception:
            pass

    print(f"[qt] Active timers: {len(active)}")
    for t, cls, name, parent_desc, thr_name, interval in active[:50]:
        print(f"  - {cls} name={name!r} interval={interval}ms parent={parent_desc} thread={thr_name!r} repr={t!r}")

    # Optionally list some “top” QObjects
    for o in qobjs[: min(len(qobjs), 50)]:
        cls, name, parent_desc, thr_name = _qt_obj_summary(o)
        print(f"  [obj] {cls} name={name!r} parent={parent_desc} thread={thr_name!r}")


def stop_and_delete_timers(app):
    from qtpy import QtCore

    # (A) Timers discoverable from Qt parent/child tree
    qt_tree_timers = app.findChildren(QtCore.QTimer)
    print(f"[qt] Timers found via app.findChildren: {len(qt_tree_timers)}")
    for t in qt_tree_timers:
        try:
            if t.isActive():
                t.stop()
            t.deleteLater()
        except Exception as e:
            print("[qt] Failed stopping tree timer:", e)

    # (B) Timers discoverable from Python GC
    import gc

    gc_timers = []
    for o in gc.get_objects():
        try:
            if isinstance(o, QtCore.QTimer):
                gc_timers.append(o)
        except Exception:
            pass

    print(f"[qt] Timers found via gc.get_objects: {len(gc_timers)}")
    for t in gc_timers:
        try:
            if t.isActive():
                t.stop()
            t.deleteLater()
        except Exception:
            pass


def close_and_delete_all_widgets(app):
    from qtpy import QtWidgets

    widgets = QtWidgets.QApplication.allWidgets()
    print(f"[qt] allWidgets(): {len(widgets)}")

    # Close top-levels first
    for w in app.topLevelWidgets():
        try:
            w.close()
        except Exception:
            pass

    # Then delete everything we can see
    for w in widgets:
        try:
            w.setParent(None)  # helps break parent cycles in some cases
        except Exception:
            pass
        try:
            w.deleteLater()
        except Exception:
            pass


def pump_events(app, rounds=50):
    from qtpy import QtCore

    for _ in range(rounds):
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        # Ensure deferred deletes run:
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


faulthandler.dump_traceback_later(timeout=14.0, repeat=True)


@pytest.fixture(scope="session")
def qapp():
    """Create a single QApplication instance for all tests.

    This fixture is session-scoped, meaning it will be created once
    for the entire test session and reused across all test files.
    """
    app = QApplication.instance()
    assert not app, "QApplication instance already exists"
    app = QApplication(sys.argv)
    yield app

    # Close remaining windows
    for window in app.topLevelWidgets():
        try:
            window.close()
        except Exception:
            pass

    # Run garbage collection and quit the application
    gc.collect()
    app.quit()
    del app
    gc.collect()
