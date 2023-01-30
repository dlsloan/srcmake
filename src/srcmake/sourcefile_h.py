import mypycheck as _chk; _chk.check(__file__)

from . import sourcefile, sourcefilefactory

import re

class CppHeaderFileFactory(sourcefilefactory.SourceFileFactory):
    name_re = re.compile('.*\.h(?:pp)?', flags=re.IGNORECASE)
    link_re = re.compile(r'\s*#\s*include\s*"([^"]*)"')
    command_comment_re = re.compile('//!(.*)')

    def scan_for_sources(self, source: 'sourcefile.SourceFile') -> None:
        cpp_path = source.path.parent / f"{source.path.stem}.cpp"
        source.env._get_source(cpp_path, None)
        super().scan_for_sources(source)

sourcefile.SourceFile.register(CppHeaderFileFactory())