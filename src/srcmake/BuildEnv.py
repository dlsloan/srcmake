import mypycheck as _chk; _chk.check(__file__)

from pathlib import Path
from typing import *

from .Target import Target

class BuildEnv:
    build_dir: Path
    package_dir: Path
    targets: Dict[Path, Target]
    source_files: Set[Path]

    def __init__(self) -> None:
        self.build_dir = Path('_build')
        self.package_dir = Path('_pkg')
        self.targets = {}
        self.source_files = set()

    def mkdir(self, path: Path) -> None:
        if path.exists():
            return

        path.mkdir(parents=True)

    def get_target(self, src: Union[Path, str], type:str='') -> Target:
        src = Path(src)

        type = Target.target_type(src, type)

        target_fname = src.stem + type
        target_path = self.to_build_dir(src.parent / target_fname)

        if src not in self.source_files:
            self.source_files.add(src)

        if target_path not in self.targets:
            self.targets[target_path] = Target(self, src, target_path, type)
            self.targets[target_path]._scan()
        else:
            assert self.targets[target_path].src == src

        return self.targets[target_path]

    def to_build_dir(self, path: Path) -> Path:
        return self.build_dir / path.relative_to(self.build_dir.parent)
