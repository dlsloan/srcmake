import mypycheck as _chk; _chk.check(__file__)

from .buildenv import BuildEnv
from .gccbuilder import GccBuilder

def main() -> None:
    import argparse
    import shutil
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--purge', action='store_true')
    args = parser.parse_args()
    env = BuildEnv()
    if (args.clean or args.purge) and env._build_dir.exists():
        shutil.rmtree(env._build_dir)
    if args.purge and env._package_dir.exists():
        shutil.rmtree(env._package_dir)
    if args.target is not None:
        exe = env.get_executable(args.target)
        build = GccBuilder(exe)
        build.make()
