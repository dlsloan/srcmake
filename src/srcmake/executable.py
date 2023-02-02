import mypycheck as _chk; _chk.check(__file__)

from pathlib import Path
from typing import *

class Executable:
    env: 'buildenv.BuildEnv'
    target: 'targ.Target'
    path: Path
    _opts: Optional[Dict[str, str]]

    def __init__(self, env: 'buildenv.BuildEnv', target: 'targ.Target') -> None:
        self.env = env
        self.target = target
        self.path = target.path.parent / target.path.stem.split('.')[0]
        self._opts = None

    @property
    def opts(self) -> Dict[str, str]:
        if self._opts is None:
            self._opts = {}
            for name, op, value in self.target.source.opts:
                if name not in self._opts and op == '+=':
                    op = ':='
                if op == '+=' and value != '':
                    self._opts[name] += ' ' + value
                elif op == ':=':
                    if value == '':
                        del self._opts[name]
                    else:
                        self._opts[name] = value
        return self._opts

from . import buildenv
from . import target as targ
