#!/usr/bin/env python3

import os
import sys
import unittest
import shutil
import tempfile

from pathlib import Path
import subprocess as sp

test_dir = Path(__file__).resolve().parent.resolve()
lib_dir = test_dir.parent / 'src'
projects_dir = test_dir / 'projects'

sys.path.insert(0, str(lib_dir))
import srcmake # type: ignore

class PackagesTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()

    def test_pulldep(self):
        shutil.copytree(projects_dir / 'packages', self.tmp_dir.name, dirs_exist_ok=True)
        proj = Path(self.tmp_dir.name) / 'proj'
        os.chdir(proj)
        env = srcmake.BuildEnv()
        target = env.get_target('main.cpp')
        assert len(env.targets) == 2
        assert len(env.source_files) == 3
        assert Path('_pkg/hello_printer/hello.h') in env.source_files
        assert Path('_pkg/hello_printer/hello.cpp') in env.source_files
        assert Path('main.cpp') in env.source_files
        assert Path('_build/main.cpp.o') in env.targets
        assert Path('_build/_pkg/hello_printer/hello.cpp.o') in env.targets
        assert Path('_pkg/hello_printer/hello.h').exists()
        assert Path('_pkg/hello_printer/hello.cpp').exists()

    def test_nested_dep(self):
        shutil.copytree(projects_dir / 'packages', self.tmp_dir.name, dirs_exist_ok=True)
        proj = Path(self.tmp_dir.name) / 'proj'
        os.chdir(proj)
        env = srcmake.BuildEnv()
        target = env.get_target('main_2_wrapper.cpp')
        assert len(env.targets) == 2
        assert len(env.source_files) == 4
        assert Path('_pkg/wrapper/wrapper.h') in env.source_files
        assert Path('_pkg/hello_printer/hello.h') in env.source_files
        assert Path('_pkg/hello_printer/hello.cpp') in env.source_files
        assert Path('main_2_wrapper.cpp') in env.source_files
        assert Path('_build/main_2_wrapper.cpp.o') in env.targets
        assert Path('_build/_pkg/hello_printer/hello.cpp.o') in env.targets
        assert Path('_pkg/wrapper/wrapper.h').exists()
        assert Path('_pkg/hello_printer/hello.h').exists()
        assert Path('_pkg/hello_printer/hello.cpp').exists()

    def test_relative_pkg(self):
        shutil.copytree(projects_dir / 'packages', self.tmp_dir.name, dirs_exist_ok=True)
        proj = Path(self.tmp_dir.name) / 'proj'
        os.chdir(proj)
        env = srcmake.BuildEnv()
        target = env.get_target('inner/main.cpp')
        assert len(env.targets) == 2
        assert len(env.source_files) == 3
        assert Path('_pkg/hello_printer/hello.h') in env.source_files
        assert Path('_pkg/hello_printer/hello.cpp') in env.source_files
        assert Path('inner/main.cpp') in env.source_files
        assert Path('_build/inner/main.cpp.o') in env.targets
        assert Path('_build/_pkg/hello_printer/hello.cpp.o') in env.targets
        assert Path('_pkg/hello_printer/hello.h').exists()
        assert Path('_pkg/hello_printer/hello.cpp').exists()

    def test_executable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.TemporaryFile() as log_file:
                shutil.copytree(projects_dir / 'packages', tmp_dir,
                                dirs_exist_ok=True)
                proj = Path(tmp_dir)
                os.chdir(proj)
                env = srcmake.BuildEnv(cwd=proj / 'proj')
                exe = env.get_executable('proj/main.cpp')
                assert exe.env == env
                assert exe.path == Path('_build/main')
                build = srcmake.Builder(exe)
                build.make(stdout=log_file.fileno(), stderr=log_file.fileno())
                output = sp.check_output(['proj/_build/main'], encoding='utf-8')
                assert output == 'Hello as const!\n'

    def test_executable_2_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.TemporaryFile() as log_file:
                shutil.copytree(projects_dir / 'packages', tmp_dir,
                                dirs_exist_ok=True)
                proj = Path(tmp_dir)
                os.chdir(proj)
                env = srcmake.BuildEnv(cwd=proj / 'proj')
                exe = env.get_executable('proj/main_2_wrapper.cpp')
                assert exe.env == env
                assert exe.path == Path('_build/main_2_wrapper')
                build = srcmake.Builder(exe)
                build.make(stdout=log_file.fileno(), stderr=log_file.fileno())
                output = sp.check_output(['proj/_build/main_2_wrapper'], encoding='utf-8')
                assert output == 'Hello as const!2\n'

    def test_executable_inner(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.TemporaryFile() as log_file:
                shutil.copytree(projects_dir / 'packages', tmp_dir,
                                dirs_exist_ok=True)
                proj = Path(tmp_dir)
                os.chdir(proj)
                env = srcmake.BuildEnv(cwd=proj / 'proj')
                exe = env.get_executable('proj/inner/main.cpp')
                assert exe.env == env
                assert exe.path == Path('_build/inner/main')
                build = srcmake.Builder(exe)
                build.make(stdout=log_file.fileno(), stderr=log_file.fileno())
                output = sp.check_output(['proj/_build/inner/main'], encoding='utf-8')
                assert output == 'Hello as const!3\n'

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        return super().tearDown()

if __name__ == '__main__':
    unittest.main()