import mypycheck as _chk; _chk.check(__file__)

import threading as _thr
import typing as _t
import inspect as _ins
import os as _os
import weakref as _wr

T = _t.TypeVar('T')

AsyncFn_T = _t.Union[_t.Callable[[], _t.Any], _t.Callable[['AsyncValue[_t.Any]'], _t.Any]]

class AsyncValue(_t.Generic[T]):
    _STATE_COMPLETE = 0
    _STATE_PENDING = 1
    _STATE_DEFERED = 2

    _cv: _thr.Condition
    _fn: AsyncFn_T
    _parent: _t.Optional['AsyncValue[_t.Any]']
    _chained: _t.List['AsyncValue[_t.Any]']
    _state: int
    _worker: _t.Optional['AsyncPool']

    def __init__(self, fn: AsyncFn_T, *, _parent: _t.Optional['AsyncValue[_t.Any]']=None, _immediate: bool=False) -> None:
        self._cv = _thr.Condition()
        self._fn = fn
        self._parent = _parent
        self._chained = []
        self._state = AsyncValue._STATE_DEFERED
        self._worker = None

        if _parent is not None:
            with _parent._cv:
                _parent._chained.append(self)
                if _immediate and _parent._state == AsyncValue._STATE_COMPLETE:
                    self.value()

    def _value(self) -> T:
        assert self._state == AsyncValue._STATE_COMPLETE
        if self._err is None:
            return self._val # type: ignore
        raise self._err
    
    def is_done(self) -> bool:
        with self._cv:
            return self._state == AsyncValue._STATE_COMPLETE

    def value(self) -> T:
        with self._cv:
            if self._state == AsyncValue._STATE_COMPLETE:
                return self._value()

            while self._state == AsyncValue._STATE_PENDING:
                self._cv.wait()

            if self._state == AsyncValue._STATE_COMPLETE:
                return self._value()

        it = iter(self.exec())
        while True:
            try:
                next(it)
            except StopIteration:
                break

        with self._cv:
            assert self._state == AsyncValue._STATE_COMPLETE
            return self._value()

    def exec(self, *, is_worker: bool=False) -> _t.Iterator[_t.Any]:
        it = iter(self._exec(is_worker=is_worker))
        try:
            next(it)
        except StopIteration:
            return iter([])
        return it

    def _exec(self, *, is_worker: bool=False) -> _t.Iterable[_t.Any]:
        with self._cv:
            if self._state != AsyncValue._STATE_DEFERED:
                return
            self._state = AsyncValue._STATE_PENDING

        yield

        try:
            if self._parent is not None:
                for _ in self._parent.exec(is_worker=is_worker):
                    yield _

            if _ins.isgeneratorfunction(self._fn):
                if self._parent is None:
                    it = iter(self._fn()) # type: ignore
                else:
                    it = iter(self._fn(self._parent)) # type: ignore

                try:
                    while True:
                        yield next(it)
                except StopIteration as stop:
                    v = stop.value
            else:
                if self._parent is None:
                    v = self._fn() # type: ignore
                else:
                    v = self._fn(self._parent) # type: ignore
            it = iter(self._set(v, None, is_worker=is_worker))
        except Exception as err:
            it = iter(self._set(None, err, is_worker=is_worker))

        while True:
            try:
                yield next(it)
            except StopIteration:
                break

    def _set(self, val: _t.Optional[T], err: _t.Optional[Exception], *, is_worker: bool=False) -> _t.Iterable[_t.Any]:
        with self._cv:
            self._val = val
            self._err = err
            self._state = AsyncValue._STATE_COMPLETE
            self._cv.notify_all()
            chained = list(self._chained)

        for ch in chained:
            for _ in ch.exec():
                yield _

        with self._cv:
            self._worker = None

    # no way to mark on_complete type in python 3.8?
    def on_complete(self, fn: AsyncFn_T) -> 'AsyncValue[_t.Any]':
        return AsyncValue(fn, _parent=self, _immediate=True)
    
    def begin(self, pool: _t.Optional['AsyncPool']=None) -> None:
        self._it = iter(self._exec(is_worker=True))
        try:
            next(self._it)
        except StopIteration:
            return

        if pool is None:
            self._worker = AsyncPool(1, single=True)
        else:
            self._worker = pool

        self._worker.queue(self)

class AsyncAssignValue(AsyncValue[T]):
    def __init__(self) -> None:
        # Special case where None fn is ok
        super().__init__(None) # type: ignore
        self._state = AsyncValue._STATE_PENDING

    def exec(self, *, is_worker: bool = False) -> _t.Iterator[_t.Any]:
        while not self.is_done():
            yield

    def begin(self, pool: _t.Optional['AsyncPool']=None) -> None:
        pass

    def set(self, val: T) -> None:
        for _ in self._set(val, None):
            pass

    def set_err(self, err: Exception) -> None:
        for _ in self._set(None, err):
            pass

class AsyncPool:
    _ncpus: int
    _cv: _thr.Condition
    _running: bool
    _pending: _t.List[AsyncValue[_t.Any]]
    _active: int
    _threads: _t.List[_thr.Thread]
    _single: bool

    def __init__(self, ncpus: _t.Optional[int]=None, single: bool=False) -> None:
        if ncpus is None:
            ncpus = _os.cpu_count()
            if ncpus is None:
                self._ncpus = 1
            else:
                self._ncpus = ncpus
        else:
            self._ncpus = ncpus

        assert self._ncpus > 0

        self._cv = _thr.Condition()
        self._running = True
        self._pending = []
        self._active = 0
        self._threads = []
        self._single = single

    def queue(self, asyncValue: AsyncValue[_t.Any]) -> None:
        with self._cv:
            self._pending.append(asyncValue)
            if len(self._pending) + self._active > len(self._threads) and len(self._threads) < self._ncpus:
                self._threads.append(_thr.Thread(target=self._mk_worker(), daemon=True))
                self._threads[-1].start()

    def _mk_worker(self) -> _t.Callable[[], None]:
        def _mk_worker2(weak_ref: '_wr.ref[AsyncPool]') -> _t.Callable[[], None]:
            def wrapped() -> None:
                return AsyncPool._worker(weak_ref)
            return wrapped
        return _mk_worker2(_wr.ref(self))
    
    def __del__(self) -> None:
        with self._cv:
            self._running = False
            self._cv.notify()

    @staticmethod
    def _worker(weak_self: '_wr.ref[AsyncPool]') -> None:
        _self = weak_self()
        while _self is not None:
            cv = _self._cv
            with cv:
                while _self is not None and len(_self._pending) == 0:
                    del _self
                    cv.wait()
                    _self = weak_self()

                if _self is None or not _self._running:
                    return

                task = _self._pending[0]
                _self._active += 1
                _self._pending = _self._pending[1:]
                if len(_self._pending) > 0:
                    _self._cv.notify()
            try:
                next(task._it)
            except StopIteration:
                if _self._single:
                    return
                else:
                    continue

            with _self._cv:
                _self._pending.append(task)
                _self._active -= 1
                _self._cv.notify()

class ActivityList:
    _cv: _thr.Condition
    _pending: _t.List[_t.Union[AsyncValue[_t.Any], 'ActivityList']]
    _complete_fns: _t.List[_t.Callable[['ActivityList'], None]]

    def __init__(self, vals: _t.Optional[_t.Iterable[_t.Union[AsyncValue[_t.Any], 'ActivityList']]]=None) -> None:
        self._cv = _thr.Condition()
        self._pending = []
        if vals is not None:
            for v in vals:
                self.add(v)
        self._complete_fns = []

    def add(self, v: _t.Union[AsyncValue[_t.Any], 'ActivityList']) -> None:
        with self._cv:
            def fn(parent: _t.Union[AsyncValue[_t.Any], 'ActivityList']) -> None:
                self._remove(parent)
            self._pending.append(v)
        v.on_complete(fn)

    def on_complete(self, fn: _t.Callable[['ActivityList'], None]) -> None:
        with self._cv:
            if len(self._pending):
                self._complete_fns.append(fn)
                return
        fn(self)

    def _remove(self, obj: _t.Union[AsyncValue[_t.Any], 'ActivityList']) -> None:
        with self._cv:
            self._pending.remove(obj)
            done = len(self._pending) == 0
            if done:
                self._cv.notify_all()
            completions = list(self._complete_fns)

        for c in completions:
            c(self)

    def wait(self) -> None:
        with self._cv:
            while len(self._pending) > 0:
                self._cv.wait()

    def is_done(self, filter: _t.Optional[_t.List[_t.Union[AsyncValue[_t.Any], 'ActivityList']]]) -> bool:
        if filter is None:
            with self._cv:
                return len(self._pending) == 0
        else:
            with self._cv:
                for p in self._pending:
                    if p not in filter:
                        return False
                return True
