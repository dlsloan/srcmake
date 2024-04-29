import mypycheck as _chk; _chk.check(__file__)

import compilers as _c
import typing as _t
import asyncfn as _async

from pathlib import Path as _Path

class FileDepBuilderBase:
    _file_types: _t.Dict[str, 'FileDepBuilderBase'] = {}

    suffix: str
    fn: _t.Optional[_t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]]

    def __init__(self, suffix: str):
        if suffix != '' and '.' not in suffix:
            suffix = '.' + suffix
        self.suffix = suffix.lower()
        self.fn = None
        assert suffix not in self._file_types
        self._file_types[suffix] = self

class FileDepBuilder(FileDepBuilderBase):
    def __init__(self, suffix: str):
        super().__init__(suffix)

    def __call__(self, fn: _t.Callable[['BuildEnv', _Path], _t.List[_Path]]) -> _t.Callable[['BuildEnv', _Path], _t.List[_Path]]:
        def run(env: 'BuildEnv', path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
            aval: _async.AsyncValue[_t.List[_Path]] = _async.AsyncValue(lambda: fn(env, path))
            aval.begin(env.pool)
            return aval
        self.fn = run
        return fn
    
class AsyncFileDepBuilder(FileDepBuilderBase):
    def __init__(self, suffix: str):
        super().__init__(suffix)

    def __call__(self, fn: _t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]) -> _t.Callable[['BuildEnv', _Path], _async.AsyncValue[_t.List[_Path]]]:
        self.fn = fn
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
    pool: _async.AsyncPool
    files: _t.Dict[_Path, BuildFile]

    def __init__(self) -> None:
        self.pool = _async.AsyncPool()
        self.files = {}

    def deps(self, _path: _t.Union[_Path, str]) -> _async.AsyncValue[_t.List[_Path]]:
        path = _Path(_path)
        if path in self.files:
            return self.files[path].deps

        suffix = path.suffix.lower()
        if suffix not in FileDepBuilder._file_types:
            raise Exception(f"Unknown file type: \"{suffix}\", {path}")
        fbuilder = FileDepBuilderBase._file_types[suffix]
        assert fbuilder.fn is not None

        file = BuildFile(path)
        self.files[path] = file
        aval = fbuilder.fn(self, path)
        aval.on_complete(lambda val: file._set(val.value()))
        return aval

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

@AsyncFileDepBuilder('.o')
def build_cc_obj_deps(env: BuildEnv, path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
    src_path = path.parent / f"{path.stem}.c"
    return _c.run_c_cpp_deps('gcc', [], src_path)

@AsyncFileDepBuilder('.o++')
def build_cxx_obj_deps(env: BuildEnv, path: _Path) -> _async.AsyncValue[_t.List[_Path]]:
    src_path = path.parent / f"{path.stem}.cpp"
    return _c.run_c_cpp_deps('g++', [], src_path)
