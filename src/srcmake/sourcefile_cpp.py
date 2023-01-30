import mypycheck as _chk; _chk.check(__file__)

from . import sourcefile, sourcefilefactory

import re

from typing import *

class CppFileFactory(sourcefilefactory.SourceFileFactory):
    name_re = re.compile('.*\.cpp', flags=re.IGNORECASE)
    link_re = re.compile(r'\s*#\s*include\s*"([^"]*)"')
    command_comment_re = re.compile('//!(.*)')

    def get_target(self, env: 'buildenv.BuildEnv', source: 'sourcefile.SourceFile') -> Optional['target.Target']:
        path = env.build_dir / f"{source.path}.o"
        return target.Target(env, path, source)

sourcefile.SourceFile.register(CppFileFactory())

from . import buildenv, target
