import mypycheck as _chk; _chk.check(__file__)

from .buildenv import BuildEnv

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    args = parser.parse_args()
