import mypycheck as _chk; _chk.check(__file__)

import argparse
import buildfile
import shlex
import subprocess as sp
import sys
import tempfile

from pathlib import Path

gdb_cmd = """
set $_exitcode = -999
catch throw
r {args}
if $_exitcode != -999
    q
end
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--clean', '-c', action='store_true')
    parser.add_argument('--build', action='store_true', help='Enforce project building (overrides exit on clean)')
    parser.add_argument('--hex', action='store_true')
    parser.add_argument('--jbin', action='store_true', help='Pack binary into json binary format (hopefully self documenting?)')
    parser.add_argument('--run-target', '-r', action='store_true', help='run target after building')
    parser.add_argument('--debug', '-g', action='store_true', help='Enable debug mode and start application in debugger if --run-target is also specified')
    parser.add_argument('-v', '--verbose', action='count', default=0)

    # pull run args out after --
    run_args = []
    app_argv = sys.argv
    for i in range(len(sys.argv)):
        if sys.argv[i] == '--':
            run_args = sys.argv[i+1:]
            app_argv = sys.argv[:i]
            break

    args = parser.parse_args(app_argv[1:])

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
    env.verbosity = args.verbose
    if args.debug:
        env.cc_flags.extend(['-g', '-O0'])
        env.cxx_flags.extend(['-g', '-O0'])
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
        if args.debug:
            with tempfile.NamedTemporaryFile() as tmp_file:
                gdb_cmd_path = Path(tmp_file.name)
                with gdb_cmd_path.open('w') as gdb_cmd_file:
                    gdb_cmd_file.write(gdb_cmd.format(args=' '.join(shlex.quote(o) for o in run_args)))
                cmd = ['gdb', '-return-child-result', '-x', str(gdb_cmd_path), str(targ)]
                if args.verbose > 0:
                    print(*[shlex.quote(c) for c in cmd], file=sys.stderr)
                sp.call(cmd)
        else:
            cmd = [str(targ)] + run_args
            if args.verbose > 0:
                print(*[shlex.quote(c) for c in cmd], file=sys.stderr)
            sp.call(cmd)
