import mypycheck as _chk; _chk.check(__file__)

from . import sourcefilefactory

from pathlib import Path
from typing import *

class SourceFile:
    factories: List[sourcefilefactory.SourceFileFactory]=[]

    @classmethod
    def register(cls, factory: sourcefilefactory.SourceFileFactory) -> None:
        cls.factories.append(factory)

    env: 'buildenv.BuildEnv'
    path: Path
    factory: sourcefilefactory.SourceFileFactory
    target: Optional['target.Target']
    links: List['SourceFile']
    _full_deps: Optional[Set[Path]]
    opts: List[Tuple[str, str, str]]

    def __init__(self, env: 'buildenv.BuildEnv', path: Path) -> None:
        self.env = env
        self.path = path
        self.links = []
        self._full_deps = None
        self.opts = []

        factory: Optional[sourcefilefactory.SourceFileFactory] = None
        for factory in self.factories:
            assert factory is not None
            if factory.name_re.match(path.name) is not None:
                break
            factory = None

        if factory is None:
            raise LookupError(f"Unknown file type {path.name}: {path}")

        env.source_files[self.path] = self

        self.factory = factory
        self.target = self.factory.get_target(self.env, self)
        self.factory.scan(self)

    def full_deps(self) -> Set[Path]:
        if self._full_deps is None:
            deps: Set[Path]=set()
            self.scan_deps(deps)
            self._full_deps = deps
        return self._full_deps

    def scan_deps(self, touched: Set[Path]) -> None:
        if self._full_deps:
            for dep in self._full_deps:
                touched.add(dep)
        else:
            touched.add(self.path)
            for link in self.links:
                link.scan_deps(touched)

# circular ref for type hints
from . import buildenv, target
