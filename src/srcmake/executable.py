import mypycheck as _chk; _chk.check(__file__)

from pathlib import Path

class Executable:
    env: 'buildenv.BuildEnv'
    target: 'targ.Target'
    path: Path

    def __init__(self, env: 'buildenv.BuildEnv', target: 'targ.Target') -> None:
        self.env = env
        self.target = target
        self.path = target.path.parent / target.path.stem.split('.')[0]

from . import buildenv
from . import target as targ
