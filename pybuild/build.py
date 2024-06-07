#!/usr/bin/env python3
import mypycheck as _chk; _chk.check(__file__)

import argparse
import threading
import subprocess as sp
import os

from yfasync import *
from builder import *
from typing import *
from pathlib import Path

# TODO: -unit-test integration too! build.py --test ut_thing.cpp, and build.py --test thing.cpp should both work if thing.cpp has UT stuff in it, and ut stuff should disapear with peproc stuffs in normal builds
#       -Need sane defaults
#       -Build commands should be constructed in build() function not a separate file
#       -Need some way of configuring build settings in source c/cpp files
#       -Incremental Unitests (some way of referencing ut's from soure files and executin on local changes)
#         -once this is done, ut on obj builds is possible :)
#       -Kernel modules ;) .ko target

# Existing file targets (usually c/c++) files don't need a target file type they are just treated as in-place files
# build targets need a builder and dep manager (override build and get_deps)
# build targets will not exist outside of a build directory
# build directory is always made in cwd
# build directory will be named target.build/
# build targets will get there absolute path added to build dir

@build_target('.c')
class CSrc(TargetFile):
    parent_target = '.o'

@build_target('.o')
class CObj(TargetFile):
    parent_target = ''

    def build(self) -> AsyncTask[None]:
        return run_process(self.env.cc, '-c', '-o', self.real_path, self.src, verbosity=env.verbosity)

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
        return run_process(self.env.cxx, '-c', '-o', self.real_path, self.src, verbosity=env.verbosity)

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
            cmd = [compiler, '-o', self.real_path] + deps
            yield from run_process(*cmd, verbosity=self.env.verbosity).yfvalue
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
        return run_process('objcopy', '-O', 'ihex', self.env.get_real_path(self.exe), self.real_path, verbosity=self.env.verbosity)

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
