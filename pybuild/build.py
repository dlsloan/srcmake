import argparse
import buildfile
import shlex
import subprocess as sp

from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    args = parser.parse_args()
    targ = Path(args.target)
    if targ.suffix.lower() == '.cpp':
        assert not Path(targ.parent / f"{targ.stem}.c").exists()
        targ = targ.parent / targ.stem
    elif targ.suffix.lower() == '.c':
        assert not Path(targ.parent / f"{targ.stem}.cpp").exists()
        targ = targ.parent / targ.stem
    else:
        print(f"Error: expected .c or .cpp file not {targ.suffix}:", targ)
    env = buildfile.BuildEnv()
    try:
        env.build(targ).value()
    except sp.CalledProcessError as err:
        print(*[shlex.quote(c) for c in err.cmd])
        lines = err.stderr.strip().split('\n')
        if len(lines) > 40:
            lines = lines[:40]
        for l in lines:
            print(l)
        print("!!!Build ERROR!!!")
        exit(1)
