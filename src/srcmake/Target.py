import mypycheck as _chk; _chk.check(__file__)

import re
import subprocess as sp

from typing import *

from pathlib import Path

if TYPE_CHECKING:
    from .BuildEnv import BuildEnv

comment_parsers:Dict[str, Any] = {
    '.c': re.compile(r'^\s*//(.*)'),
    '.cpp': re.compile(r'^\s*//(.*)'),
    '.h': re.compile(r'^\s*//(.*)'),
    '.hpp': re.compile(r'^\s*//(.*)'),
}

include_parsers:Dict[str, Any] = {
    '.c': re.compile(r'^\s*#\s*include\s*"([^"]*)"'),
    '.cpp': re.compile(r'^\s*#\s*include\s*"([^"]*)"'),
    '.h': re.compile(r'^\s*#\s*include\s*"([^"]*)"'),
    '.hpp': re.compile(r'^\s*#\s*include\s*"([^"]*)"'),
}

opt_re = re.compile(r'\s*\+\s*(lopt|gopt)\s*([a-zA-Z0-9_\.]+)\s*(.*)')

class Target:
    env: 'BuildEnv'
    src: Path
    path: Path
    lopts: Dict[str, str]
    gopts: Dict[str, str]
    type: Tuple[str, str]
    file_deps: List['Target']

    @classmethod
    def target_type(cls, src: Path, type: str) -> str:
        if src.suffix == '.c' or src.suffix == '.cpp':
            if type.count('.') == 1:
                type = src.suffix + type
            return type
        else:
            return src.suffix

    def __init__(self, env: 'BuildEnv', src: Path, path: Path, type: str) -> None:
        self.env = env
        self.src = src
        self.path = path
        self.lopts = {}
        self.gopts = {}
        self.type = (src.suffix, type)
        self.file_deps = []

    def make(self, stdout: int=-1, stderr: int=-1) -> None:
        self.env.mkdir(self.path.parent)

        if (self.type[1] == ''):
            objs:List[str] = []
            for t in self.env.targets:
                target = self.env.targets[t]
                if target.type[1].endswith('.o'):
                    target.make(stdout=stdout, stderr=stderr)
                    objs.append(str(target.path))
            sp.check_call(['g++', '-o', str(self.path)] + objs,
                           stdout=stdout, stderr=stderr)
        elif self.type[1].endswith('.o'):
            sp.check_call(['g++', '-c', str(self.src), '-o', str(self.path)],
                          stdout=stdout, stderr=stderr)

    def _scan(self) -> None:
        if self.type == ('.c', ''):
            self.env.get_target(self.src, '.o')
        elif self.type == ('.cpp', ''):
            self.env.get_target(self.src, '.o')

        suffix = self.src.suffix.lower()
        if suffix not in comment_parsers:
            raise LookupError('Unknown file type: ' + suffix)

        comment_re = comment_parsers[suffix]
        include_re = include_parsers[suffix]
        with self.src.open() as f:
            for line in f:
                m = comment_re.match(line)
                if m is not None:
                    m = opt_re.match(m.group(1))
                    if m is not None:
                        if m.group(1) == 'lopt':
                            opts = self.lopts
                        else:
                            opts = self.gopts

                        if m.group(2) in opts:
                            opts[m.group(2)] += ' ' + m.group(3).strip()
                        else:
                            opts[m.group(2)] = m.group(3).strip()
                        continue
                m = include_re.match(line)
                if m is not None:
                    file = self.src.parent / m.group(1)
                    assert file.exists() and (file.suffix == '.h' or file.suffix == '.hpp')
                    self.file_deps.append(self.env.get_target(file))
                    file = file.parent / (file.stem + ".c")
                    if file.exists():
                        self.env.get_target(file, '.o')
                    file = file.parent / (file.stem + '.cpp')
                    if file.exists():
                        self.env.get_target(file, '.o')
