from weakref import ref
import types

"""
CallbackRegistry is a class taken from matplotlib.cbook.

http://sourceforge.net/p/matplotlib/code/HEAD/tree/trunk/matplotlib/lib/matplotlib/cbook.py
"""


class CallbackRegistry:
    """
    Handle registering and disconnecting for a set of signals and
    callbacks::

       signals = 'eat', 'drink', 'be merry'

       def oneat(x):
           print 'eat', x

       def ondrink(x):
           print 'drink', x

       callbacks = CallbackRegistry(signals)

       ideat = callbacks.connect('eat', oneat)
       iddrink = callbacks.connect('drink', ondrink)

       #tmp = callbacks.connect('drunk', ondrink) # this will raise a ValueError

       callbacks.process('drink', 123)    # will call oneat
       callbacks.process('eat', 456)      # will call ondrink
       callbacks.process('be merry', 456) # nothing will be called
       callbacks.disconnect(ideat)        # disconnect oneat
       callbacks.process('eat', 456)      # nothing will be called

    In practice, one should always disconnect all callbacks when they
    are no longer needed to avoid dangling references (and thus memory
    leaks).  However, real code in matplotlib rarely does so, and due
    to its design, it is rather difficult to place this kind of code.
    To get around this, and prevent this class of memory leaks, we
    instead store weak references to bound methods only, so when the
    destination object needs to die, the CallbackRegistry won't keep
    it alive.  The Python stdlib weakref module can not create weak
    references to bound methods directly, so we need to create a proxy
    object to handle weak references to bound methods (or regular free
    functions).  This technique was shared by Peter Parente on his
    `"Mindtrove" blog
    <http://mindtrove.info/articles/python-weak-references/>`_.
    """

    def __init__(self, signals):
        """
        *signals* a sequence of signal names, or None if not providing
        any validation on connect.
        """
        self.signals = set(signals) if signals is not None else None
        # mapping from signal to a set of proxy objects for callbacks
        self.callbacks = dict()
        # proxy objects for callbacks (so we can use weak references)
        self._proxy_objs = dict()

    def __del__(self):
        # Just in case there are any lingering references
        self.disconnect_all()

    def connect(self, signal, func):
        """
        Register *func* to be called when signal *signal* is generated.
        Returns the id of the callback for disconnection.

        *signal* can be a signal name or list of signal names, or None.
        """
        if signal is None:
            signals = []
        elif isinstance(signal, list):
            signals = signal
        else:
            signals = [signal]
        callback_ids = []
        for sig in signals:
            if self.signals is not None and sig not in self.signals:
                raise ValueError("Unknown signal: %s" % sig)
            if sig not in self.callbacks:
                self.callbacks[sig] = set()
            if func not in self._proxy_objs:
                self._proxy_objs[func] = self._BoundMethodProxy(func)
            proxy = self._proxy_objs[func]
            self.callbacks[sig].add(proxy)
            callback_ids.append((sig, id(proxy)))
        # return the id of the proxy object, not the function itself
        return callback_ids[0] if len(callback_ids) == 1 else callback_ids

    def disconnect(self, callback_ids):
        """
        Disconnect the callback registered with callback id *callback_ids*.
        """
        if not isinstance(callback_ids, list):
            callback_ids = [callback_ids]
        for callback_id in callback_ids:
            if isinstance(callback_id, tuple):
                signal, proxy_id = callback_id
            else:
                # Assume it's a single signal callback id
                signal, proxy_id = callback_id
            if signal in self.callbacks:
                for proxy in list(self.callbacks[signal]):
                    if id(proxy) == proxy_id:
                        self.callbacks[signal].discard(proxy)
                        break

    def disconnect_all(self):
        """Disconnect all callbacks registered in this registry."""
        self.callbacks.clear()
        self._proxy_objs.clear()

    def process(self, signal, *args, **kwargs):
        """
        Process signal *signal*.

        All functions registered to receive this signal will be called
        with *args* and **kwargs*.
        """
        if signal not in self.callbacks:
            return
        # don't iterate directly over the set in case callbacks disconnect
        # during iteration
        for proxy in list(self.callbacks[signal]):
            # wrap in try/except so if a callback function throws we'll
            # be able to remove the dead proxy
            try:
                proxy(*args, **kwargs)
            except ReferenceError:
                self.callbacks[signal].discard(proxy)

    class _BoundMethodProxy(object):
        """
        Our proxy objects need to be hashable and weak-referenceable.
        Based on code from Peter Parente's "Mindtrove" blog:
        http://mindtrove.info/articles/python-weak-references/
        """

        def __init__(self, callback):
            if isinstance(callback, types.MethodType):
                # callback is bound method
                self._obj = ref(callback.__self__)
                self._func = callback.__func__
                self._class = callback.__self__.__class__
            else:
                # callback is a regular function or callable
                self._obj = None
                self._func = callback
                self._class = None

        def __call__(self, *args, **kwargs):
            if self._obj is not None:
                # bound method
                obj = self._obj()
                if obj is None:
                    raise ReferenceError
                return self._func(obj, *args, **kwargs)
            else:
                # regular function
                return self._func(*args, **kwargs)

        def __eq__(self, other):
            if isinstance(other, CallbackRegistry._BoundMethodProxy):
                if self._obj is not None and other._obj is not None:
                    return self._func == other._func and self._obj() == other._obj()
                elif self._obj is None and other._obj is None:
                    return self._func == other._func
            return False

        def __ne__(self, other):
            return not self == other

        def __hash__(self):
            return id(self._func)
