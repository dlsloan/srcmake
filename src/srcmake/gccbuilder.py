import mypycheck as _chk; _chk.check(__file__)

import subprocess as sp
import sys

from typing import *

class GccBuilder:
    env: 'buildenv.BuildEnv'
    exe: 'executable.Executable'

    def __init__(self, exe: 'executable.Executable') -> None:
        self.env = exe.env
        self.exe = exe

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

            print("\tg++", end='', file=f)
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

        print(f"\tg++ -I../_pkg -c {ssrc} -o {starg}", file=f)
        print(file=f)

from . import buildenv, executable, target
