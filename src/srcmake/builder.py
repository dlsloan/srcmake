import mypycheck as _chk; _chk.check(__file__)

import subprocess as sp
import sys

from typing import *

class Builder:
    obj_builder: str='g++'
    obj_builder_args: str = '-g -Wall -Werror'
    link_builder: str='g++'
    link_builder_args: str = '-g'

    env: 'buildenv.BuildEnv'
    exe: 'executable.Executable'

    def __init__(self, exe: 'executable.Executable') -> None:
        self.env = exe.env
        self.exe = exe
        if 'obj-builder' in exe.opts:
            self.obj_builder = exe.opts['obj-builder']
        if 'obj-builder-args' in exe.opts:
            self.obj_builder_args = exe.opts['obj-builder-args']
        if 'link-builder' in exe.opts:
            self.link_builder = exe.opts['link-builder']
        if 'link-builder-args' in exe.opts:
            self.link_builder_args = exe.opts['link-builder-args']

    def make(self, *, stdout: int=-1, stderr: int=-1) -> None:
        if stdout < 0:
            stdout = sys.stdout.fileno()
        if stderr < 0:
            stderr = sys.stderr.fileno()

        self.env._build_dir.mkdir(parents=True, exist_ok=True)
        with (self.env._build_dir / 'Makefile').open('w') as f:
            ptarg = self.env.build_rel(self.exe.path)
            (self.env._build_dir / ptarg.parent).mkdir(parents=True, exist_ok=True)
            starg = str(ptarg)
            if ' ' in starg:
                starg = f'"{starg}"'
            print(f"{starg}:", end='', file=f)
            for targ in self.env.targets.values():
                spath = str(self.env.build_rel(targ.path))
                if ' ' in spath:
                    spath = f'"{spath}"'
                print(f" {spath}", end='', file=f)
            print(file=f)

            print(f"\t{self.link_builder} {self.link_builder_args}", end='', file=f)
            for targ in self.env.targets.values():
                spath = str(self.env.build_rel(targ.path))
                if ' ' in spath:
                    spath = f'"{spath}"'
                print(f" {spath}", end='', file=f)
            print(f" -o {starg}", file=f)
            print(file=f)

            for targ in self.env.targets.values():
                self.make_target(targ, f)

        sp.check_call(['make'], cwd=self.env._build_dir, stdout=stdout, stderr=stderr)

    def make_target(self, targ: 'target.Target', f: Any) -> None:
        ptarg = self.env.build_rel(targ.path)
        (self.env._build_dir / ptarg.parent).mkdir(parents=True, exist_ok=True)
        starg = str(ptarg)
        if ' ' in starg:
            starg = f'"{starg}"'
        print(f"{starg}:", end='', file=f)
        for dep in targ.source.full_deps():
            spath = str(self.env.build_rel(dep))
            if ' ' in spath:
                spath = f'"{spath}"'
            print(f" {spath}", end='', file=f)
        print(file=f)

        ssrc = str(self.env.build_rel(targ.source.path))
        if ' ' in ssrc:
            ssrc = f'"{ssrc}"'

        print(f"\t{self.obj_builder} {self.obj_builder_args} -I../_pkg -c {ssrc} -o {starg}", file=f)
        print(file=f)

from . import buildenv, executable, target
