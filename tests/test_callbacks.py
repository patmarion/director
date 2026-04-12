import gc
import weakref

from director.callbacks import CallbackRegistry


class Recorder:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def callback(self, value):
        self.calls.append((self.name, value))


def test_bound_methods_on_distinct_instances_are_registered_separately():
    registry = CallbackRegistry(["event"])
    calls = []
    first = Recorder("first", calls)
    second = Recorder("second", calls)

    first_id = registry.connect("event", first.callback)
    second_id = registry.connect("event", second.callback)

    assert first_id != second_id

    registry.process("event", 5)

    assert calls == [("first", 5), ("second", 5)]


def test_bound_method_connections_do_not_keep_instances_alive():
    registry = CallbackRegistry(["event"])
    calls = []
    listener = Recorder("listener", calls)
    listener_ref = weakref.ref(listener)

    registry.connect("event", listener.callback)

    del listener
    gc.collect()

    assert listener_ref() is None

    registry.process("event", 7)

    assert calls == []
    assert registry.getCallbacks("event") == []
