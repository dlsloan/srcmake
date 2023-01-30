#!/usr/bin/env python3

import os
import sys
import unittest
import shutil
import tempfile

from pathlib import Path

test_dir = Path(__file__).resolve().parent.resolve()
lib_dir = test_dir.parent / 'src'
projects_dir = test_dir / 'projects'

sys.path.insert(0, str(lib_dir))
import srcmake # type: ignore

class BasicHelloWorldTests(unittest.TestCase):
    def test_build_dirs(self):
        env = srcmake.BuildEnv()
        assert env.build_dir == Path('_build')
        assert env.package_dir == Path('_pkg')

    def test_hello_world_target(self):
        os.chdir(test_dir)
        env = srcmake.BuildEnv()
        target = env.get_target('projects/hello_world/main.cpp')
        assert target.env == env
        assert target.source.path == Path('projects/hello_world/main.cpp')
        assert target.path == Path('_build/projects/hello_world/main.cpp.o')
        assert Path('_build/projects/hello_world/main.cpp.o') in env.targets
        assert Path('projects/hello_world/main.cpp') in env.source_files

    def test_hello_world_cwd_target(self):
        os.chdir(test_dir)
        env = srcmake.BuildEnv(cwd='projects/hello_world')
        target = env.get_target('projects/hello_world/main.cpp')
        assert target.env == env
        assert target.source.path == Path('main.cpp')
        assert target.path == Path('_build/main.cpp.o')
        assert Path('_build/main.cpp.o') in env.targets
        assert Path('main.cpp') in env.source_files

    def test_unknown_source(self):
        env = srcmake.BuildEnv()
        with self.assertRaises(LookupError):
            env.get_target('projects/hello_world/readme.txt')

class MultiFileHelloWorldTests(unittest.TestCase):
    def setUp(self):
        os.chdir(projects_dir / 'multi_file_hello_world')

    def test_header_target(self):
        env = srcmake.BuildEnv()
        target = env.get_target('hello_world.h')
        assert target is None
        assert Path('hello_world.h') in env.source_files
        assert len(env.source_files[Path('hello_world.h')].links) == 0
        assert Path('hello_world.cpp') in env.source_files

    def test_header_target(self):
        env = srcmake.BuildEnv()
        target = env.get_target('hello_world.cpp')
        assert target.source.path == Path('hello_world.cpp')
        assert Path('hello_world.cpp') in env.source_files
        assert len(target.source.links) == 1
        assert target.source.links[0].path == Path('hello_world.h')
        assert Path('hello_world.h') in env.source_files

    def test_full_target(self):
        env = srcmake.BuildEnv()
        target = env.get_target('main.cpp')
        assert target.source.path == Path('main.cpp')
        assert len(env.targets) == 2
        assert env.targets[Path('_build/main.cpp.o')].source.path == Path('main.cpp')
        assert env.targets[Path('_build/main.cpp.o')].path == Path('_build/main.cpp.o')
        assert env.targets[Path('_build/hello_world.cpp.o')].source.path == Path('hello_world.cpp')
        assert env.targets[Path('_build/hello_world.cpp.o')].path == Path('_build/hello_world.cpp.o')
        assert len(env.source_files) == 3
        src_main = env.source_files[Path('main.cpp')]
        assert src_main.target == env.targets[Path('_build/main.cpp.o')]
        assert src_main.path == Path('main.cpp')
        assert src_main.links == [env.source_files[Path('hello_world.h')]]
        src_hello_cpp = env.source_files[Path('hello_world.cpp')]
        assert src_hello_cpp.target == env.targets[Path('_build/hello_world.cpp.o')]
        assert src_hello_cpp.path == Path('hello_world.cpp')
        assert src_hello_cpp.links == [env.source_files[Path('hello_world.h')]]
        src_hello_h = env.source_files[Path('hello_world.h')]
        assert src_hello_h.target is None
        assert src_hello_h.path == Path('hello_world.h')
        assert len(src_hello_h.links) == 0

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

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        return super().tearDown()

if __name__ == '__main__':
    unittest.main()
