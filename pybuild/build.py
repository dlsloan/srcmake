import mypycheck as _chk; _chk.check(__file__)

import argparse
import buildfile
import shlex
import subprocess as sp
import sys

from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--clean', '-c', action='store_true')
    parser.add_argument('--build', action='store_true', help='Enforce project building (overrides exit on clean)')
    parser.add_argument('--hex', action='store_true')
    parser.add_argument('--jbin', action='store_true', help='Pack binary into json binary format (hopefully self documenting?)')
    parser.add_argument('--run-target', '-r', action='store_true', help='run target after building')
    # TODO: --debug, -d target (auto-start dgb)
    args = parser.parse_args()
    targ = Path(args.target)
    if targ.suffix == '':
        pass # short hand for easy tab conpletion on rebuilds
    elif targ.suffix.lower() == '.cpp':
        assert not Path(targ.parent / f"{targ.stem}.c").exists()
        targ = targ.parent / targ.stem
    elif targ.suffix.lower() == '.c':
        assert not Path(targ.parent / f"{targ.stem}.cpp").exists()
        targ = targ.parent / targ.stem
    else:
        print(f"Error: expected .c or .cpp file not {targ.suffix}:", targ, file=sys.stderr)

    if args.jbin:
        targ = targ.parent / f"{targ.stem}.jbin"
    elif args.hex:
        targ = targ.parent / f"{targ.stem}.hex"

    env = buildfile.BuildEnv()
    if args.clean:
        build_outputs = {
            '.jbin', '.hex', '.o', '.o++', ''
        }
        env.scan_deps(targ)
        for path in env.files:
            if path.exists() and path.suffix.lower() in build_outputs:
                path.unlink()
        if not args.run_target and not args.build:
            exit(0)
    try:
        env.build(targ).value()
    except sp.CalledProcessError as err:
        print(*[shlex.quote(c) for c in err.cmd], file=sys.stderr)
        lines = err.stderr.strip().split('\n')
        if len(lines) > 40:
            lines = lines[:40]
        for l in lines:
            print(l, file=sys.stderr)
        print("!!!Build ERROR!!!", file=sys.stderr)
        exit(1)
    if args.run_target:
        # TODO: run jbin targets in emulator
        assert targ.suffix == '', "Only exe targets supported right now"
        sp.call([targ])
