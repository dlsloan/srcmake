import mypycheck as _chk; _chk.check(__file__)

import asyncfn as _async
import compilers as _c
import threading as _thr
import typing as _t
import sys as _sys

from pathlib import Path as _Path

class FileBuilderBase:
    _file_types: _t.Dict[str, 'FileBuilderBase'] = {}

    suffix: str
    dep_fn: _t.Optional[_t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]]
    build_fn: _t.Optional[_t.Callable[['BuildEnv', 'BuildFile'], None]]

    def __init__(self, suffix: str) -> None:
        if suffix != '' and '.' not in suffix:
            suffix = '.' + suffix
        self.suffix = suffix.lower()
        self.dep_fn = None
        self.build_fn = None

    def _assign_dep_fn(self, fn: _t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]) -> None:
        if self.suffix not in self._file_types:
            self._file_types[self.suffix] = self
        self._file_types[self.suffix].dep_fn = fn

    def _assign_build_fn(self, fn: _t.Callable[['BuildEnv', 'BuildFile'], None]) -> None:
        if self.suffix not in self._file_types:
            self._file_types[self.suffix] = self
        self._file_types[self.suffix].build_fn = fn

class FileDepBuilder(FileBuilderBase):
    def __init__(self, suffix: str) -> None:
        super().__init__(suffix)

    def __call__(self, fn: _t.Callable[['BuildEnv', _Path], _t.List[_Path]]) -> _t.Callable[['BuildEnv', _Path], _t.List[_Path]]:
        def run(env: 'BuildEnv', path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
            aval: _async.AsyncValue[_t.List[_Path]] = _async.AsyncValue(lambda: fn(env, path))
            aval.begin(env.pool)
            return aval
        self._assign_dep_fn(run)
        return fn
    
class AsyncFileDepBuilder(FileBuilderBase):
    def __init__(self, suffix: str) -> None:
        super().__init__(suffix)

    def __call__(self, fn: _t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]) -> _t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]:
        self._assign_dep_fn(fn)
        return fn
    
class FileBuilder(FileBuilderBase):
    def __init__(self, suffix: str)-> None:
        super().__init__(suffix)
    
    def __call__(self, fn: _t.Callable[['BuildEnv', 'BuildFile'], None]) -> _t.Callable[['BuildEnv', 'BuildFile'], None]:
        self._assign_build_fn(fn)
        return fn

class BuildFile:
    path: _Path
    _deps: _async.AsyncAssignValue[_t.List[_Path]]

    def __init__(self, path: _Path) -> None:
        self.path = path
        self._deps = _async.AsyncAssignValue()

    @property
    def deps(self) -> _async.AsyncValue[_t.List[_Path]]:
        return self._deps

    def _set(self, val: _t.List[_Path]) -> None:
        self._deps.set(val)

    def _err(self, err: Exception) -> None:
        self._deps.set_err(err)

class BuildEnv:
    _lck: _thr.Lock
    pool: _async.AsyncPool
    files: _t.Dict[_Path, BuildFile]
    _build_results: _t.Dict[_Path, _async.AsyncValue[float]]
    verbosity: int=0
    cc_flags: _t.List[str]
    cxx_flags: _t.List[str]

    def __init__(self) -> None:
        self._lck = _thr.Lock()
        self.pool = _async.AsyncPool()
        self.files = {}
        self._build_results = {}
        self.cc_flags = ['-Wall', '-Werror']
        self.cxx_flags = ['-Wall', '-Werror']

    def scan_deps(self, _path: _t.Union[_Path, str]) -> None:
        path = _Path(_path)
        scanned = {path}
        pending = [self.deps(path)]
        while len(pending) > 0:
            ds = pending[0].value()
            pending = pending[1:]
            for d in ds:
                if d in scanned:
                    continue
                pending.append(self.deps(d))
                scanned.add(d)

    def deps(self, _path: _t.Union[_Path, str]) -> _async.AsyncValue[_t.List[_Path]]:
        with self._lck:
            path = _Path(_path)
            if path in self.files:
                return self.files[path].deps

            suffix = path.suffix.lower()
            if suffix not in FileDepBuilder._file_types:
                raise Exception(f"Unknown file type: \"{suffix}\", {path}")
            fbuilder = FileBuilderBase._file_types[suffix]
            assert fbuilder.dep_fn is not None, f"No dep scanner for type: \"{suffix}\", {path}"

            file = BuildFile(path)
            self.files[path] = file
            aval = fbuilder.dep_fn(self, path)
            aval.on_complete(lambda val: file._set(val.value()))
            return aval

    def build(self, _path: _t.Union[_Path, str]) -> _async.AsyncValue[float]:
        def run() -> _t.Iterator[_t.Any]:
            path = _Path(_path)
            adeps = self.deps(path)

            while not adeps.is_done():
                yield
            deps = adeps.value()

            targ_mtime: float
            if path.exists():
                targ_mtime = path.stat().st_mtime
            else:
                targ_mtime = 0

            newest_dep: float = 0

            pending: _t.List[_async.AsyncValue[float]] = []
            for d in deps:
                pending.append(self.build(d))
            for p in pending:
                while not p.is_done():
                    yield
                newest_dep = max(newest_dep, p.value())

            suffix = path.suffix.lower()
            if suffix not in FileDepBuilder._file_types:
                raise Exception(f"Unknown file type: \"{suffix}\", {path}")
            fbuilder = FileBuilderBase._file_types[suffix]
            assert fbuilder.build_fn is not None, f"No builder for type: \"{suffix}\", {path}"

            if targ_mtime == 0 or targ_mtime < newest_dep:
                fbuilder.build_fn(self, self.files[path])

            return path.stat().st_mtime

        with self._lck:
            if _Path(_path) in self._build_results:
                return self._build_results[_Path(_path)]
            aval: _async.AsyncValue[float] = _async.AsyncValue(run)
            aval.begin(self.pool)
            self._build_results[_Path(_path)] = aval
            return aval

@FileDepBuilder('.jbin')
def build_jbin_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    hex_path = path.parent / f"{path.stem}.hex"
    return [hex_path]

@FileBuilder('.jbin')
def build_jbin(env: BuildEnv, file: BuildFile) -> None:
    hex_path = file.path.parent / f"{file.path.stem}.hex"
    print('Build:', file.path, file=_sys.stderr)
    _c.run_jbin_build(hex_path=hex_path, jbin_path=file.path, verbosity=env.verbosity)

@FileDepBuilder('.hex')
def build_hex_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    exe_path = path.parent / f"{path.stem}"
    return [exe_path]

@FileBuilder('.hex')
def build_hex(env: BuildEnv, file: BuildFile) -> None:
    exe_path = file.path.parent / f"{file.path.stem}"
    print('Build:', file.path, file=_sys.stderr)
    _c.run_hex_build('objcopy', [], exe_path=exe_path, hex_path=file.path, verbosity=env.verbosity)

@FileDepBuilder('')
def build_exe_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    src_cc_path = path.parent / f"{path.stem}.c"
    src_cxx_path = path.parent / f"{path.stem}.cpp"
    if src_cc_path.exists():
        obj_path = path.parent / f"{path.stem}.o"
        hdr_suffix = '.h'
        src_suffix = '.c'
        obj_suffix = '.o'
    elif src_cxx_path.exists():
        obj_path = path.parent / f"{path.stem}.o++"
        hdr_suffix = '.hpp'
        src_suffix = '.cpp'
        obj_suffix = '.o++'
    else:
        raise Exception(f"Could not find c++ or c source for target {path}")
    deps = [obj_path]
    pending_deps = [env.deps(obj_path)]

    while len(pending_deps) > 0:
        p = pending_deps[0]
        pending_deps = pending_deps[1:]
        for d in p.value():
            if d.suffix.lower() == hdr_suffix:
                src_path = d.parent / f"{d.stem}{src_suffix}"
                if src_path.exists():
                    obj_path = d.parent / f"{d.stem}{obj_suffix}"
                if obj_path not in deps:
                    pending_deps.append(env.deps(obj_path))
                    deps.append(obj_path)
    return deps

@FileBuilder('')
def build_exe(env: BuildEnv, file: BuildFile) -> None:
    first_dep: _t.Optional[_Path]=None
    for d in file.deps.value():
        first_dep = d
    assert first_dep is not None, f"Something went wrong, no deps found for: {file.path}"
    print('Build:', file.path, file=_sys.stderr)
    if first_dep.suffix.lower() == '.o++':
        _c.run_c_cpp_exe_build('g++', env.cxx_flags, obj_paths=file.deps.value(), exe_path=file.path, verbosity=env.verbosity)
    elif first_dep.suffix.lower() == '.o':
        _c.run_c_cpp_exe_build('gcc', env.cc_flags, obj_paths=file.deps.value(), exe_path=file.path, verbosity=env.verbosity)
    else:
        raise Exception(f"Something when wrong, deps should be either .o or .o++, found: {first_dep.suffix}")

@AsyncFileDepBuilder('.o')
def build_c_obj_deps(env: BuildEnv, path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
    src_path = path.parent / f"{path.stem}.c"
    return _c.run_c_cpp_deps('gcc', env.cc_flags, src_path, verbosity=env.verbosity)

@FileBuilder('.o')
def build_cc_obj(env: BuildEnv, file: BuildFile) -> None:
    src_path = file.path.parent / f"{file.path.stem}.c"
    print('Build:', src_path, '->', file.path, file=_sys.stderr)
    _c.run_c_cpp_obj_build('gcc', env.cc_flags, src_path=src_path, obj_path=file.path, verbosity=env.verbosity)

@FileDepBuilder('.c')
def build_c_file_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    return []

@FileBuilder('.c')
def build_c_file(env: BuildEnv, file: BuildFile) -> None:
    pass

@FileDepBuilder('.h')
def build_h_file_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    return []

@FileBuilder('.h')
def build_h_file(env: BuildEnv, file: BuildFile) -> None:
    pass

@AsyncFileDepBuilder('.o++')
def build_cxx_obj_deps(env: BuildEnv, path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
    src_path = path.parent / f"{path.stem}.cpp"
    return _c.run_c_cpp_deps('g++', env.cxx_flags, src_path, verbosity=env.verbosity)

@FileBuilder('.o++')
def build_cxx_obj(env: BuildEnv, file: BuildFile) -> None:
    src_path = file.path.parent / f"{file.path.stem}.cpp"
    print('Build:', src_path, '->', file.path, file=_sys.stderr)
    _c.run_c_cpp_obj_build('g++', env.cxx_flags, src_path=src_path, obj_path=file.path, verbosity=env.verbosity)

@FileDepBuilder('.cpp')
def build_cpp_file_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    return []

@FileBuilder('.cpp')
def build_cpp_file(env: BuildEnv, file: BuildFile) -> None:
    pass

@FileDepBuilder('.hpp')
def build_hpp_file_deps(env: BuildEnv, path: _Path) -> _t.List[_Path]:
    return []

@FileBuilder('.hpp')
def build_hpp_file(env: BuildEnv, file: BuildFile) -> None:
    pass
