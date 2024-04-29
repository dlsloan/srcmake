import mypycheck as _chk; _chk.check(__file__)

import asyncfn as _async
import subprocess as _sp
import typing as _t

from pathlib import Path as _Path

def _parse_dep_output(output: str) -> _t.List[_Path]:
    in_sep = False
    parts = ['']
    while len(output):
        if output[0] == '\\':
            output = output[1:]
            if in_sep and output[0].isspace():
                output = output[1:]
                continue
            else:
                in_sep = False
        elif output[0].isspace():
            if not in_sep:
                parts.append('')
            in_sep = True
            output = output[1:]
            continue
        in_sep = False
        parts[-1] += output[0]
        output = output[1:]
    return [_Path(s) for s in parts[1:]]

def run_c_cpp_deps(compiler: str, args: _t.Sequence[str], path: _t.Union[str, _Path]) -> _async.AsyncValue[_t.List[_Path]]:
    def run() -> _t.Iterable[_Path]:
        src = _Path(path)
        cmd = [compiler]
        cmd += args
        cmd += ['-MM', '-MG', '-fdiagnostics-color', str(src)]
        output = _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE)
        assert isinstance(output, str)
        output = output.strip()
        return _parse_dep_output(output)
    return _async.AsyncValue(run)

def run_c_cpp_obj_build(compiler: str, args: _t.Sequence[str], src_path: _Path, obj_path: _Path) -> None:
    cmd = [compiler]
    cmd += args
    cmd += ['-c', '-o', str(obj_path), str(src_path)]
    _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE)

def run_c_cpp_exe_build(compiler: str, args: _t.Sequence[str], obj_paths: _t.Sequence[_Path], exe_path: _Path) -> None:
    cmd = [compiler]
    cmd += args
    cmd += ['-o', str(exe_path)]
    cmd += [str(p) for p in obj_paths]
    _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE)
