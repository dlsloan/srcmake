#!/usr/bin/env python3
import mypycheck as _chk; _chk.check(__file__)

import argparse
import threading
import subprocess as sp
import os

from yfasync import *
from compilers import *
from typing import *
from pathlib import Path

def cached(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def wrap(self: Any) -> Any:
        cache_name = f"_cache_{fn.__name__}"
        if not hasattr(self, cache_name):
            setattr(self, cache_name, fn(self))
        return getattr(self, cache_name)
    return wrap

# TODO: -unit-test integration too! build.py --test ut_thing.cpp, and build.py --test thing.cpp should both work if thing.cpp has UT stuff in it, and ut stuff should disapear with peproc stuffs in normal builds
#       -Need sane defaults
#       -Build commands should be constructed in build() function not a separate file
#       -Need some way of configuring build settings in source c/cpp files
#       -Kernel modules ;) .ko target

# Existing file targets (usually c/c++) files don't need a target file type they are just treated as in-place files
# build targets need a builder and dep manager (override build and get_deps)
# build targets will not exist outside of a build directory
# build directory is always made in cwd
# build directory will be named target.build/
# build targets will get there absolute path added to build dir
class TargetFile:
    # alows for simpler .c/.cpp definitions without having to rewrite get_realpath for that class
    is_build_target_type: Optional[bool]=None
    parent_target: Optional[str]=None

    key_path: Path
    virtual_path: Path
    real_path: Path
    env: 'BuildEnv'

    @classmethod
    def is_build_target(cls) -> bool:
        return cls.build.__code__ is not TargetFile.build.__code__

    @classmethod
    def get_realpath(cls, path: Path, *, env: 'BuildEnv') -> Path:
        if cls.is_build_target():
            return env.build_dir / '.obj' / str(path.resolve())[1:]
        else:
            return path

    def __init__(self, path: Path, *, env: 'BuildEnv') -> None:
        self.env = env
        self.key_path = path.resolve()
        self.virtual_path = path
        self.real_path = self.get_realpath(path, env=env)

    @property
    def stem(self) -> str:
        return self.virtual_path.stem

    def get_deps(self) -> AsyncTask[List[Path]]:
        return AsyncTask([])

    def build(self) -> AsyncTask[None]:
        return AsyncTask(None)

target_types: Dict[str, Type[TargetFile]]={}

U = TypeVar('U')
def it_max(values: Iterable[U]) -> Optional[U]:
    ret: Optional[U] = None
    for v in values:
        if ret is None:
            ret = v
        else:
            ret = max(v, ret) # type: ignore
    return ret

class BuildEnv:
    _lck: threading.Lock
    build_dir: Path
    cc: str
    cxx: str
    root_target: Path
    verbosity: int
    targets: Dict[Path, TargetFile]

    def __init__(self, root_target: Union[Path, str]) -> None:
        root_target = Path(root_target)
        self._lck = threading.Lock()
        self.cc = 'gcc'
        self.cxx = 'g++'
        self.verbosity = 1
        self.targets = {}
        if root_target.suffix not in target_types:
            raise NotImplementedError(f"Target type '{root_target.suffix}' unknown: {root_target}")
        while target_types[root_target.suffix].parent_target is not None:
            root_target = root_target.parent / f"{root_target.stem}{target_types[root_target.suffix].parent_target}"
        self.build_dir = Path(f"{root_target.stem}.build")
        self.root_target = root_target

    def get_target(self, path: Union[Path, str]) -> TargetFile:
        path = Path(path)
        if path.resolve() in self.targets:
            return self.targets[path.resolve()]
        elif path.suffix in target_types:
            self.targets[path.resolve()] = target_types[path.suffix](path, env=self)
            return self.targets[path.resolve()]
        elif path.exists():
            self.targets[path.resolve()] = TargetFile(path, env=self)
            return self.targets[path.resolve()]
        else:
            raise NotImplementedError(f"Unknown type: {path.suffix}, for: {path}")

    def get_real_path(self, path: Path) -> Path:
        return self.get_target(path).real_path

    def get_root_target(self) -> TargetFile:
        return self.get_target(self.root_target)

    def build(self, target_path: Path, *, _built: Optional[Set[Path]]=None) -> AsyncTask[os.stat_result]:
        def run() -> Generator[None, None, os.stat_result]:
            priv_built: Set[Path]
            if _built is None:
                priv_built = set()
            else:
                priv_built = _built

            target = self.get_target(target_path)

            if target_path.resolve() in priv_built:
                return target.real_path.stat()

            deps = yield from target.get_deps().yfvalue
            active: List[AsyncTask[os.stat_result]]=[]
            for d in deps:
                active.append(self.build(d, _built=priv_built))
            dep_stats = yield from AsyncTask.yf_all(active)
            newest = it_max(st.st_mtime for st in dep_stats)
            if target.real_path.exists() and (newest is None or target.real_path.stat().st_mtime >= newest):
                return target.real_path.stat()

            assert target_path.resolve() not in priv_built
            target.real_path.parent.mkdir(parents=True, exist_ok=True)
            yield from target.build().yfvalue
            priv_built.add(target_path.resolve())

            return target.real_path.stat()

        return AsyncTask(run())

def build_target(suffix: str) -> Callable[[Type[TargetFile]], Type[TargetFile]]:
    def dec(cls: Type[TargetFile]) -> Type[TargetFile]:
        assert suffix not in target_types
        target_types[suffix] = cls
        return cls
    return dec

@build_target('.c')
class CSrc(TargetFile):
    parent_target = '.o'

@build_target('.o')
class CObj(TargetFile):
    parent_target = ''

    def build(self) -> AsyncTask[None]:
        return run_c_cpp_obj_build(self.env.cc, [], self.src, self.real_path, env.verbosity)

    @property
    def src(self) -> Path:
        return self.virtual_path.parent / f"{self.virtual_path.stem}.c"

    @cached
    def get_deps(self) -> AsyncTask[List[Path]]:
        src_path = self.virtual_path.parent / f"{self.stem}.c"
        return run_c_cpp_deps('gcc', [], src_path, 0)

@build_target('.cpp')
class CppSrc(TargetFile):
    is_build_target_type = False
    parent_target = '.o++'

@build_target('.o++')
class CppObj(TargetFile):
    parent_target = ''

    def build(self) -> AsyncTask[None]:
        return run_c_cpp_obj_build(self.env.cxx, [], self.src, self.real_path, env.verbosity)

    @property
    def src(self) -> Path:
        return self.virtual_path.parent / f"{self.virtual_path.stem}.cpp"

    @cached
    def get_deps(self) -> AsyncTask[List[Path]]:
        src_path = self.virtual_path.parent / f"{self.stem}.cpp"
        return run_c_cpp_deps('g++', [], src_path, 0)
    
@build_target('')
class ExeFile(TargetFile):
    @classmethod
    def get_realpath(cls, path: Path, *, env: BuildEnv) -> Path:
        return env.build_dir / 'bin' / path.stem

    def build(self) -> AsyncTask[None]:
        def run() -> Generator[None, None, None]:
            deps = yield from self.get_deps().yfvalue
            compiler = self.env.cc
            for d in deps:
                if str(d).endswith('.o++'):
                    compiler = self.env.cxx
            deps = [self.env.get_real_path(d) for d in deps]
            yield from run_c_cpp_exe_build(compiler, [], deps, self.real_path, env.verbosity).yfvalue
        return AsyncTask(run())

    @cached
    def get_deps(self) -> AsyncTask[List[Path]]:
        def run() -> Generator[None, None, List[Path]]:
            c_src = self.virtual_path.parent / f"{self.stem}.c"
            cpp_src = self.virtual_path.parent / f"{self.stem}.cpp"
            if (c_src).exists():
                root_dep = self.virtual_path.parent / f"{self.stem}.o"
            elif (cpp_src).exists():
                root_dep = self.virtual_path.parent / f"{self.stem}.o++"
            else:
                raise NotImplementedError(f"No deps found for: {self.virtual_path}\n  searched: {c_src}\n  and:      {cpp_src}")

            known_deps: Set[Path] = set([root_dep.resolve()])
            deps: List[Path] = [root_dep]
            pending = [self.env.get_target(root_dep).get_deps()]
            while len(pending) > 0:
                pdeps = yield from pending[0].yfvalue
                pending = pending[1:]
                new_deps = set(pdeps)
                for d in new_deps:
                    if d.suffix == '.h':
                        src = d.parent / f"{d.stem}.c"
                        obj = d.parent / f"{d.stem}.o"
                    elif d.suffix == '.hpp':
                        src = d.parent / f"{d.stem}.cpp"
                        obj = d.parent / f"{d.stem}.o++"
                    else:
                        continue

                    if obj.resolve() not in known_deps and src.exists():
                        known_deps.add(obj.resolve())
                        deps.append(obj)
                        pending.append(self.env.get_target(obj).get_deps())
            return deps
        return AsyncTask(run())

@build_target('.hex')
class HexDump(TargetFile):
    @classmethod
    def get_realpath(cls, path: Path, *, env: BuildEnv) -> Path:
        return env.build_dir / 'bin' / f"{path.stem}.hex"

    def build(self) -> AsyncTask[None]:
        return run_hex_build('objcopy', [], self.env.get_real_path(self.exe), self.real_path, self.env.verbosity)

    @property
    def exe(self) -> Path:
        return self.virtual_path.parent / self.virtual_path.stem

    @cached
    def get_deps(self) -> AsyncTask[List[Path]]:
        return AsyncTask([self.exe])

@build_target('.jbin')
class JBinDump(TargetFile):
    @classmethod
    def get_realpath(cls, path: Path, *, env: BuildEnv) -> Path:
        return env.build_dir / 'bin' / f"{path.stem}.jbin"

    def build(self) -> AsyncTask[None]:
        return run_jbin_build(self.env.get_real_path(self.hex), self.real_path, self.env.verbosity)

    @property
    def hex(self) -> Path:
        return self.virtual_path.parent / f"{self.virtual_path.stem}.hex"

    @cached
    def get_deps(self) -> AsyncTask[List[Path]]:
        return AsyncTask([self.hex])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--deps', action='store_true')
    args = parser.parse_args()

    env = BuildEnv(args.target)
    if args.deps:
        for v in env.get_target(args.target).get_deps().value:
            print(v)
    else:
        try:
            env.build(env.root_target).value
        except sp.CalledProcessError as err:
            print("Build failed: ", *err.cmd)
            print(err.stderr)
