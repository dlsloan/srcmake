import threading

class SingletonRefs:
    locals = threading.local()
    local_events = threading.local()

    def __init__(self, id):
        if not hasattr(SingletonRefs.locals, 'inst'):
            SingletonRefs.locals.inst = {}
        self._id = id
        if id not in SingletonRefs.locals.inst:
            SingletonRefs.locals.inst[id] = {}
            self._storage = None
            self._completions = None
        self._is_outer = False
        self._wrapper = None
        if __debug__:
            self._has_entered = False
            self._has_exited = False


    @property
    def _storage(self):
        return SingletonRefs.locals.inst[self._id]['storage']
    @_storage.setter
    def _storage(self, value):
        SingletonRefs.locals.inst[self._id]['storage'] = value


    @property
    def _completions(self):
        return SingletonRefs.locals.inst[self._id]['comp']
    @_completions.setter
    def _completions(self, value):
        SingletonRefs.locals.inst[self._id]['comp'] = value


    def values(self):
        return self._storage.values()


    def extend_scope(self, value=None):
        return SingletonExtension(self, value)


    def set_on_complete(self, id, func):
        self._completions[id] = func


    def _complete(self):
        events = self._completions
        if events is not None:
            for event in events:
                events[event](self)
        self._completions = None
        self._storage = None


    def __enter__(self):
        assert not self._has_entered
        if __debug__:
            self._has_entered = True

        if self._storage is None:
            self._storage = {}
            self._is_outer = True
            self._completions = {}

        return self


    def __exit__(self, ex_type, ex_val, ex_trace):
        assert self._has_entered
        assert not self._has_exited
        if __debug__:
            self._has_exited = True
        if self._is_outer:
            self._complete()
        if ex_val is not None and self._wrapper is not None:
            # Excersize wrapper since it will be skipped
            with self._wrapper:
                pass


    def __contains__(self, value):
        return value in self._storage


    def __getitem__(self, k):
        return self._storage[k]


    def __setitem__(self, k, v):
        self._storage[k] = v


    def __delitem__(self, k):
        del self._storage[k]


    def __len__(self):
        return len(self._storage)


if __debug__:
    def SingletonRefs__del__(self):
        assert self._has_entered == self._has_exited
    SingletonRefs.__del__ = SingletonRefs__del__



class SingletonExtension:
    def __init__(self, singleton, value):
        self._singleton = singleton
        self._value = value
        self._is_outer = singleton._is_outer
        singleton._wrapper = self
        if singleton._is_outer:
            singleton._is_outer = False
        if __debug__:
            self._has_entered = False
            self._has_exited = False


    def __enter__(self):
        assert not self._has_entered
        if __debug__:
            self._has_entered = True
        self._singleton._wrapper = None

        return self._value


    def __exit__(self, *pa, **ka):
        assert not self._has_exited
        if __debug__:
            self._has_exited = True
        if self._is_outer:
            self._singleton._complete()


if __debug__:
    def SingletonExtension__del__(self):
        assert self._has_entered == self._has_exited
    SingletonExtension.__del__ = SingletonExtension__del__