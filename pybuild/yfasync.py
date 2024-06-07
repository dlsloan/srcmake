import mypycheck as _chk; _chk.check(__file__)

import inspect as _ins
import multiprocessing as _mp
import time as _time
import threading as _thr
import typing as _t
import weakref as _wr

T = _t.TypeVar('T')

class AsyncTask(_t.Generic[T]):
    @classmethod
    def yf_all(cls, tasks: '_t.List[AsyncTask[T]]') -> _t.Generator[None, None, _t.List[T]]:
        indicies = set(range(len(tasks)))
        to_drop: _t.Set[int] = set()
        ret: _t.List[_t.Optional[T]]=[None]*len(tasks)
        while len(indicies):
            for i in indicies:
                if tasks[i].step():
                    to_drop.add(i)
                    ret[i] = tasks[i].value
                else:
                    yield
            indicies -= to_drop
            to_drop = set()
        for r in ret:
            assert r is not None
        return ret # type: ignore

    _lck: _thr.Lock
    _generator: _t.Optional[_t.Generator[None, None, T]]=None
    _value: _t.Optional[_t.Tuple[_t.Optional[T], _t.Optional[Exception]]]=None

    def __init__(self, res: _t.Union[T, _t.Generator[None, None, T]]) -> None:
        self._lck = _thr.Lock()
        if _ins.isgenerator(res):
            self._generator = res
        else:
            # value resolved with _ins.isgenerator above
            self._value = (res, None) # type: ignore

    @property
    def done(self) -> bool:
        return self._value is not None # should be atomic, checkup on this with GIL rework

    @property
    def value(self) -> T:
        while not self.done:
            self.step()
        assert self._value is not None
        val, err = self._value
        if err is not None:
            raise err
        return val # type: ignore

    # intended for use with 'yield for' operation
    @property
    def yfvalue(self) -> _t.Generator[None, None, T]:
        while not self.step():
            yield
        return self.value

    # Returns true if this step completed the task or it was already complete
    # false othewise
    def step(self) -> bool:
        with self._lck:
            if not self.done:
                try:
                    assert self._generator is not None
                    next(self._generator)
                except StopIteration as stop:
                    self._value = (stop.value, None)
                except Exception as err:
                    self._value = (None, err)
            return self.done

class ThreadPool:
    _cv: _thr.Condition
    _nthreads: int
    _pending: _t.List['SyncTask[_t.Any]']
    _workers: int
    _active: int

    def __init__(self, nthreads: _t.Optional[int]=None) -> None:
        self._cv = _thr.Condition()
        if nthreads is None:
            self._nthreads = _mp.cpu_count()
        else:
            assert nthreads > 0
            self._nthreads = nthreads
        self._pending = []
        self._workers = 0
        self._active = 0

    def queue(self, task: 'SyncTask[_t.Any]') -> None:
        with self._cv:
            self._pending.append(task)
            if self._active + len(self._pending) > self._workers and self._workers < self._nthreads:
                self._start_worker()
            self._cv.notify()

    def _start_worker(self) -> None:
        self._workers += 1
        self._active += 1
        _thr.Thread(target=self._worker, args=[_wr.ref(self)], daemon=True).start()

    def __del__(self) -> None:
        with self._cv:
            self._workers = 0
            self._cv.notify_all()

    @classmethod
    def _worker(cls, pool: '_wr.ref[ThreadPool]') -> None:
        _self: _t.Optional['ThreadPool']=pool()
        while _self is not None and _self._workers > 0:
            cv = _self._cv
            with cv:
                _self._active -= 1
                while len(_self._pending) == 0:
                    del _self
                    cv.wait()
                    _self = pool()
                    if _self is None or _self._workers == 0:
                        return

                task = _self._pending[0]
                _self._active += 1
                _self._pending = _self._pending[1:]
                if len(_self._pending) > 0:
                    _self._cv.notify()
            # use try_exec for early escape if someone else is already executing this
            task.try_exec()

_system_thread_pool = ThreadPool()

class SyncTask(_t.Generic[T]):
    _lck: _thr.Lock
    _fn: _t.Callable[[], T]
    as_async: AsyncTask[T]
    _wait_delay: float
    _last_check: _t.Optional[float]=None
    _value: _t.Optional[_t.Tuple[_t.Optional[T], _t.Optional[Exception]]]=None

    def __init__(self, fn: _t.Callable[[], T], *, pool: _t.Optional[ThreadPool]=None, wait_delay: float=0.001) -> None:
        self._lck = _thr.Lock()
        self._fn = fn # type: ignore
        self.as_async = AsyncTask(self._async_value())
        self._wait_delay = wait_delay
        if pool is None:
            _system_thread_pool.queue(self)
        else:
            pool.queue(self)

    def _async_value(self) -> _t.Generator[None, None, T]:
        while not self.done:
            if self._last_check is not None:
                if _time.time() - self._last_check < self._wait_delay:
                    _time.sleep(self._wait_delay)
            self._last_check = _time.time()
            yield
        return self.value

    @property
    def done(self) -> bool:
        return self._value is not None

    @property
    def value(self) -> T:
        return self.run()

    def try_exec(self) -> bool:
        if self._lck.acquire(blocking=False):
            try:
                if self._value is not None:
                    return True
                self._value = (self._fn(), None) # type: ignore
            except Exception as err:
                self._value = (None, err)
            finally:
                self._lck.release()
            return True
        return False

    def exec(self) -> None:
        with self._lck:
            if self._value is not None:
                return

            try:
                self._value = (self._fn(), None) # type: ignore
            except Exception as err:
                self._value = (None, err)

    def run(self) -> T:
        if self._value is None:
            self.exec()
        assert self._value is not None
        val, err = self._value
        if err is not None:
            raise err
        return val # type: ignore
