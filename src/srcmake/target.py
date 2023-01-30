import mypycheck as _chk; _chk.check(__file__)

from pathlib import Path

class Target:
    env: 'buildenv.BuildEnv'
    path: Path
    source: 'sourcefile.SourceFile'

    def __init__(self, env: 'buildenv.BuildEnv', path: Path, source: 'sourcefile.SourceFile') -> None:
        self.env = env
        self.path = path
        self.source = source

        env.targets[self.path] = self

from . import buildenv, sourcefile