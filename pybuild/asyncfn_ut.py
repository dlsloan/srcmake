import threading
import unittest

from asyncfn import *

class BasicTest(unittest.TestCase):
    def test_basic(self):
        obj = { 'cnt': 0 }
        def run():
            obj['cnt'] += 1
            return obj['cnt']
        val = AsyncValue(run)
        assert obj['cnt'] == 0
        assert val.value() == 1
        assert obj['cnt'] == 1
        assert val.value() == 1
        assert obj['cnt'] == 1

    def test_exec(self):
        obj = { 'cnt': 0 }
        def run():
            obj['cnt'] += 1
            return obj['cnt']
        v = AsyncValue(run)
        assert obj['cnt'] == 0
        it = iter(v.exec())
        assert obj['cnt'] == 0
        try:
            next(it)
            assert False, "Should have completed"
        except StopIteration as stop:
            pass
        assert obj['cnt'] == 1
        assert v.value() == 1
        assert obj['cnt'] == 1

    def test_basic_yield(self):
        obj = { 'cnt': 0 }
        def run():
            obj['cnt'] += 1
            yield
            obj['cnt'] += 1
            return obj['cnt']
        val = AsyncValue(run)
        assert obj['cnt'] == 0
        assert val.value() == 2
        assert obj['cnt'] == 2
        assert val.value() == 2
        assert obj['cnt'] == 2

    def test_exec_yield(self):
        obj = { 'cnt': 0 }
        def run():
            obj['cnt'] += 1
            yield
            obj['cnt'] += 1
            return obj['cnt']
        v = AsyncValue(run)
        assert obj['cnt'] == 0
        it = iter(v.exec())
        assert obj['cnt'] == 0
        next(it)
        assert obj['cnt'] == 1
        try:
            next(it)
            assert False, "Should have completed"
        except StopIteration as stop:
            pass
        assert obj['cnt'] == 2
        assert v.value() == 2
        assert obj['cnt'] == 2

    def test_exec_chained_yield(self):
        obj = { 'cnt': 0 }
        def run():
            obj['cnt'] += 1
            yield
            obj['cnt'] += 1
            return obj['cnt']
        def run_child(p):
            v = p.value()
            obj['cnt'] += 100
            yield
            obj['cnt'] += 100
            return (v + obj['cnt']) * 1000
        v = AsyncValue(run)
        vc = v.on_complete(run_child)
        assert obj['cnt'] == 0
        it = iter(vc.exec())
        assert obj['cnt'] == 0
        next(it)
        assert obj['cnt'] == 1
        next(it)
        assert obj['cnt'] == 102
        try:
            next(it)
            assert False, "Should have completed"
        except StopIteration as stop:
            pass
        assert obj['cnt'] == 202
        assert vc.value() == 204000
        assert obj['cnt'] == 202
        assert v.value() == 2
        assert obj['cnt'] == 202

    def test_background(self):
        obj = { 'cnt': 0, 'b': threading.Barrier(2, timeout=5) }
        def run():
            obj['cnt'] += 1
            obj['b'].wait()
            obj['cnt'] += 1
            return obj['cnt'] * 100
        v = AsyncValue(run)
        v.begin()
        obj['b'].wait()
        assert v.value() == 200
        assert obj['cnt'] == 2

    def test_pool(self):
        obj = { 'cnt1': 0, 'cnt2': 0, 'b': threading.Barrier(3, timeout=5) }
        def run1():
            obj['cnt1'] += 1
            obj['b'].wait()
            obj['cnt1'] += 1
            return obj['cnt1'] * 100
        def run2():
            obj['cnt2'] += 10
            obj['b'].wait()
            obj['cnt2'] += 10
            return obj['cnt2'] * 100
        pool = AsyncPool(2)
        v1 = AsyncValue(run1)
        v2 = AsyncValue(run2)
        v1.begin(pool)
        v2.begin(pool)
        obj['b'].wait()
        assert v1.value() == 200
        assert obj['cnt1'] == 2
        assert v2.value() == 2000
        assert obj['cnt2'] == 20
        del pool

    def test_small_pool(self):
        mtx = threading.Lock()
        threads = {}
        def run(ret):
            def _run():
                with mtx:
                    threads[threading.current_thread().name] = True
                return ret
            return _run
        pool = AsyncPool(2)
        v = []
        for i in range(256):
            v.append(AsyncValue(run(i)))
        for i in range(256):
            v[i].begin(pool)
        for i in range(256):
            assert v[i].value() == i
        assert len(threads) <= 2

if __name__ == '__main__':
    unittest.main()