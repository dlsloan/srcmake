#!/usr/bin/env python3

import os
import sys
import unittest
import shutil
import tempfile

import subprocess as sp

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

    def test_executable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.TemporaryFile() as log_file:
                shutil.copytree(projects_dir / 'hello_world', tmp_dir,
                                dirs_exist_ok=True)
                proj = Path(tmp_dir)
                os.chdir(proj)
                env = srcmake.BuildEnv()
                exe = env.get_executable('main.cpp')
                assert exe.env == env
                assert exe.path == Path('_build/main')
                build = srcmake.Builder(exe)
                build.make(stdout=log_file.fileno(), stderr=log_file.fileno())
                output = sp.check_output(['./_build/main'], encoding='utf-8')
                assert output == 'Hello World\n'

    def test_executable_opts(self):
        os.chdir(test_dir)
        env = srcmake.BuildEnv(cwd='projects/hello_world')
        exe = env.get_executable('projects/hello_world/main.cpp')
        assert 'obj-builder-args' in exe.opts
        assert exe.opts['obj-builder-args'] == '-Wall -Werror -fno-exceptions'
        assert 'link-builder-args' in exe.opts
        assert exe.opts['link-builder-args'] == '-fno-exceptions'

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

    def test_executable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.TemporaryFile() as log_file:
                shutil.copytree(projects_dir / 'multi_file_hello_world', tmp_dir,
                                dirs_exist_ok=True)
                proj = Path(tmp_dir)
                os.chdir(proj)
                env = srcmake.BuildEnv()
                exe = env.get_executable('main.cpp')
                assert exe.env == env
                assert exe.path == Path('_build/main')
                build = srcmake.Builder(exe)
                build.make(stdout=log_file.fileno(), stderr=log_file.fileno())
                output = sp.check_output(['./_build/main'], encoding='utf-8')
                assert output == 'hello world from print func!\n'

if __name__ == '__main__':
    unittest.main()
