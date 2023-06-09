import mypycheck as _chk; _chk.check(__file__)

from .buildenv import BuildEnv
from .builder import Builder

def main() -> None:
    import argparse
    import shutil
    import subprocess as sp
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--purge', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    env = BuildEnv()
    if (args.clean or args.purge) and env._build_dir.exists():
        shutil.rmtree(env._build_dir)
    if args.purge and env._package_dir.exists():
        shutil.rmtree(env._package_dir)
    if args.target is not None:
        exe = env.get_executable(args.target)
        build = Builder(exe)
        try:
            build.make()
            if args.run:
                sp.check_call([str(env.cwd / exe.path)])
        except sp.CalledProcessError:
            exit(1)
