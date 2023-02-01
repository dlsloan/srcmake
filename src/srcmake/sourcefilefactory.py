import mypycheck as _chk; _chk.check(__file__)

import re
import subprocess as sp
import shutil

from pathlib import Path
from typing import *

def run_package(env: 'buildenv.BuildEnv', path: Path) -> None:
    pkg_file = env.cwd / path
    if not pkg_file.exists():
        raise FileNotFoundError(pkg_file)
    pkg_dir = env._package_dir / pkg_file.stem
    if pkg_dir.exists():
        return

    pkg_dir.mkdir(parents=True)
    try:
        sp.check_call([str(pkg_file)], cwd=pkg_dir)
    except:
        shutil.rmtree(pkg_dir)
        raise

class SourceFileFactory:
    name_re = re.compile('//') #slash should not match anything
    link_re = re.compile('_______________________________________()')
    command_comment_re = re.compile('_______________________________________()')

    package_command_re = re.compile(r'\s*package\s*"([^"]*)"')

    def get_target(self, env: 'buildenv.BuildEnv', source: 'sourcefile.SourceFile') -> Optional['target.Target']:
        return None

    def scan_for_sources(self, source: 'sourcefile.SourceFile') -> None:
        src_path = source.env.cwd / source.path
        with src_path.open('r') as f:
            lineno = 0
            for line in f:
                lineno += 1

                try:
                    m = self.link_re.match(line)
                    if m is not None:
                        linked = source.env._get_source(source.path.parent / m.group(1), Path(m.group(1)))
                        if linked is None:
                            raise FileNotFoundError(f"File not found: {source.path.parent / m.group(1)}")
                        source.links.append(linked)
                        continue
                
                    m = self.command_comment_re.match(line)
                    if m is not None:
                        m = self.package_command_re.match(m.group(1))
                        if m is not None:
                            run_package(source.env, source.path.parent / m.group(1))
                            continue
                        continue

                except FileNotFoundError as err:
                        raise FileNotFoundError(f"File not found when scanning {source.path}:{lineno}, original error: {err}")


from . import buildenv, sourcefile, target
