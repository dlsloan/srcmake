import mypycheck as _chk; _chk.check(__file__)

from . import target, sourcefile, executable

# import source file types, these are not directly used, just here for
# registration
from . import sourcefile_cpp, sourcefile_h

from pathlib import Path
from typing import *

class BuildEnv:
    cwd: Path
    _build_dir: Path
    build_dir: Path
    _package_dir: Path
    package_dir: Path
    targets: Dict[Path, 'target.Target']
    source_files: Dict[Path, 'sourcefile.SourceFile']

    def __init__(self, *, cwd: Union[str, Path]='') -> None:
        self.cwd = Path(cwd)
        if not self.cwd.is_absolute():
            self.cwd = Path.cwd() / self.cwd
        self._build_dir = self.cwd / '_build'
        self.build_dir = self.local_path(self._build_dir)
        self._package_dir = self.cwd / '_pkg'
        self.package_dir = self.local_path(self._package_dir)
        self.targets = {}
        self.source_files = {}

    # paths are local here
    def _get_source(self, path: Path, inc_path: Optional[Path]) -> Optional['sourcefile.SourceFile']:
        if path in self.source_files:
            return self.source_files[path]
        if (self.cwd / path).exists():
            return sourcefile.SourceFile(self, path)
        elif inc_path is not None and (self._package_dir / inc_path).exists():
            path = self.package_dir / inc_path
            return sourcefile.SourceFile(self, path)
        return None

    # paths are shell pats here
    def get_source(self, path: Union[str, Path]) -> 'sourcefile.SourceFile':
        source_path = self.local_path(Path(path))
        source = self._get_source(source_path, None)
        if source is None:
            raise FileNotFoundError(f"File not found: {path}")
        return source

    # paths are shell pats here
    def get_target(self, source_path: Union[str, Path]) -> Optional['target.Target']:
        source = self.get_source(source_path)
        return source.target

    def get_executable(self, source_path: Union[str, Path]) -> 'executable.Executable':
        target = self.get_target(source_path)
        assert target is not None, f"Not convetable to executable: {source_path}"
        return executable.Executable(self, target)

    def local_path(self, path: Path) -> Path:
        if not path.is_absolute():
            path = Path.cwd() / path

        for i in range(1000):
            if i == 0:
                return path.relative_to(self.cwd)
            else:
                prepend = '/'.join(['_p_'] * i)
                return Path(prepend) / path.relative_to(self.cwd.parents[i-1])
        raise ValueError(f"Path depth limit exceeded {path}->{self.cwd}")

    def build_path(self, path: Path) -> Path:
        return self.build_dir / self.local_path(path)

    def build_rel(self, path: Path) -> Path:
        path = self.cwd / path
        for i in range(1000):
            try:
                if i == 0:
                    return path.relative_to(self._build_dir)
                else:
                    prepend = '/'.join(['..'] * i)
                    return Path(prepend) / path.relative_to(self._build_dir.parents[i-1])
            except ValueError:
                pass
        raise ValueError(f"Path depth limit exceeded {path}->{self._build_dir}")
