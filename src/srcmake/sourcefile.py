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

    def __init__(self, env: 'buildenv.BuildEnv', path: Path) -> None:
        self.env = env
        self.path = path
        self.links = []

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
        self.factory.scan_for_sources(self)

# circular ref for type hints
from . import buildenv, target
