import mypycheck as _chk; _chk.check(__file__)

import yfasync as _async
import base64 as _b64
import os as _os
import shlex as _sh
import subprocess as _sp
import sys as _sys
import threading as _thr
import typing as _t

from pathlib import Path as _Path


def cached(fn: _t.Callable[[_t.Any], _t.Any]) -> _t.Callable[[_t.Any], _t.Any]:
    def wrap(self: _t.Any) -> _t.Any:
        cache_name = f"_cache_{fn.__name__}"
        if not hasattr(self, cache_name):
            setattr(self, cache_name, fn(self))
        return getattr(self, cache_name)
    return wrap

class TargetFile:
    # alows for simpler .c/.cpp definitions without having to rewrite get_realpath for that class
    is_build_target_type: _t.Optional[bool]=None
    parent_target: _t.Optional[str]=None

    key_path: _Path
    virtual_path: _Path
    real_path: _Path
    env: 'BuildEnv'

    @classmethod
    def is_build_target(cls) -> bool:
        return cls.build.__code__ is not TargetFile.build.__code__

    @classmethod
    def get_realpath(cls, path: _Path, *, env: 'BuildEnv') -> _Path:
        if cls.is_build_target():
            return env.build_dir / '.obj' / str(path.resolve())[1:]
        else:
            return path

    def __init__(self, path: _Path, *, env: 'BuildEnv') -> None:
        self.env = env
        self.key_path = path.resolve()
        self.virtual_path = path
        self.real_path = self.get_realpath(path, env=env)

    @property
    def stem(self) -> str:
        return self.virtual_path.stem

    def get_deps(self) -> _async.AsyncTask[_t.List[_Path]]:
        return _async.AsyncTask([])

    def build(self) -> _async.AsyncTask[None]:
        return _async.AsyncTask(None)

target_types: _t.Dict[str, _t.Type[TargetFile]]={}

U = _t.TypeVar('U')
def it_max(values: _t.Iterable[U]) -> _t.Optional[U]:
    ret: _t.Optional[U] = None
    for v in values:
        if ret is None:
            ret = v
        else:
            ret = max(v, ret) # type: ignore
    return ret

class BuildEnv:
    _lck: _thr.Lock
    build_dir: _Path
    cc: str
    cxx: str
    root_target: _Path
    verbosity: int
    targets: _t.Dict[_Path, TargetFile]

    def __init__(self, root_target: _t.Union[_Path, str]) -> None:
        root_target = _Path(root_target)
        self._lck = _thr.Lock()
        self.cc = 'gcc'
        self.cxx = 'g++'
        self.verbosity = 1
        self.targets = {}
        if root_target.suffix not in target_types:
            raise NotImplementedError(f"Target type '{root_target.suffix}' unknown: {root_target}")
        while target_types[root_target.suffix].parent_target is not None:
            root_target = root_target.parent / f"{root_target.stem}{target_types[root_target.suffix].parent_target}"
        self.build_dir = _Path(f"{root_target.stem}.build")
        self.root_target = root_target

    def get_target(self, path: _t.Union[_Path, str]) -> TargetFile:
        path = _Path(path)
        if path.resolve() in self.targets:
            return self.targets[path.resolve()]
        elif path.suffix in target_types:
            self.targets[path.resolve()] = target_types[path.suffix](path, env=self)
            return self.targets[path.resolve()]
        elif path.exists():
            self.targets[path.resolve()] = TargetFile(path, env=self)
            return self.targets[path.resolve()]
        else:
            raise NotImplementedError(f"Unknown type: {path.suffix}, for: {path}")

    def get_real_path(self, path: _Path) -> _Path:
        return self.get_target(path).real_path

    def get_root_target(self) -> TargetFile:
        return self.get_target(self.root_target)

    def build(self, target_path: _Path, *, _built: _t.Optional[_t.Set[_Path]]=None) -> _async.AsyncTask[_os.stat_result]:
        def run() -> _t.Generator[None, None, _os.stat_result]:
            priv_built: _t.Set[_Path]
            if _built is None:
                priv_built = set()
            else:
                priv_built = _built

            target = self.get_target(target_path)

            if target_path.resolve() in priv_built:
                return target.real_path.stat()

            deps = yield from target.get_deps().yfvalue
            active: _t.List[_async.AsyncTask[_os.stat_result]]=[]
            for d in deps:
                active.append(self.build(d, _built=priv_built))
            dep_stats = yield from _async.AsyncTask.yf_all(active)
            newest = it_max(st.st_mtime for st in dep_stats)
            if target.real_path.exists() and (newest is None or target.real_path.stat().st_mtime >= newest):
                return target.real_path.stat()

            assert target_path.resolve() not in priv_built
            target.real_path.parent.mkdir(parents=True, exist_ok=True)
            yield from target.build().yfvalue
            priv_built.add(target_path.resolve())

            return target.real_path.stat()

        return _async.AsyncTask(run())

def build_target(suffix: str) -> _t.Callable[[_t.Type[TargetFile]], _t.Type[TargetFile]]:
    def dec(cls: _t.Type[TargetFile]) -> _t.Type[TargetFile]:
        assert suffix not in target_types
        target_types[suffix] = cls
        return cls
    return dec

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

def run_c_cpp_deps(compiler: str, args: _t.Sequence[str], path: _t.Union[str, _Path], verbosity: int=0) -> _async.AsyncTask[_t.List[_Path]]:
    def run() -> _t.List[_Path]:
        src = _Path(path)
        cmd = [compiler]
        cmd += args
        cmd += ['-MM', '-MG', '-fdiagnostics-color', str(src)]
        if verbosity > 1:
            print(*[_sh.quote(c) for c in cmd], file=_sys.stderr)
        output = _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE)
        assert isinstance(output, str)
        output = output.strip()
        return _parse_dep_output(output)
    return _async.SyncTask(run).as_async

def run_c_cpp_obj_build(compiler: str, args: _t.Sequence[str], src_path: _Path, obj_path: _Path, verbosity: int=0) -> _async.AsyncTask[None]:
    def run() -> None:
        cmd = [compiler]
        cmd += args
        cmd += ['-c', '-o', str(obj_path), str(src_path)]
        if verbosity > 0:
            print(*[_sh.quote(c) for c in cmd], file=_sys.stderr)
        out = _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE).strip()
        if verbosity > 2 and out != '':
            print(out, file=_sys.stderr)
    return _async.SyncTask(run).as_async

def run_c_cpp_exe_build(compiler: str, args: _t.Sequence[str], obj_paths: _t.Sequence[_Path], exe_path: _Path, verbosity: int=0) -> _async.AsyncTask[None]:
    def run() -> None:
        cmd = [compiler]
        cmd += args
        cmd += ['-o', str(exe_path)]
        cmd += [str(p) for p in obj_paths]
        if verbosity > 0:
            print(*[_sh.quote(c) for c in cmd], file=_sys.stderr)
        out = _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE).strip()
        if verbosity > 2 and out != '':
            print(out, file=_sys.stderr)
    return _async.SyncTask(run).as_async

def run_hex_build(compiler: str, args: _t.Sequence[str], exe_path: _Path, hex_path: _Path, verbosity: int=0) -> _async.AsyncTask[None]:
    def run() -> None:
        cmd = [compiler]
        cmd += args
        cmd += ['-O', 'ihex', str(exe_path), str(hex_path)]
        if verbosity > 0:
            print(*[_sh.quote(c) for c in cmd], file=_sys.stderr)
        out = _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE).strip()
        if verbosity > 2 and out != '':
            print(out, file=_sys.stderr)
    return _async.SyncTask(run).as_async

def run_jbin_build(hex_path: _Path, jbin_path: _Path, verbosity: int=0) -> _async.AsyncTask[None]:
    def run() -> None:
        if verbosity > 0:
            print('hex-jbin', _sh.quote(str(hex_path)), _sh.quote(str(jbin_path)), file=_sys.stderr)
        try:
            with hex_path.open('r') as hex_file, jbin_path.open('w') as jbin_file:
                # Intel hex decoder
                # https://en.wikipedia.org/wiki/Intel_HEX
                decoded: _t.Dict[_t.Union[int, str], _t.Union[int, bytes]] = {}
                offset = 0
                for line in hex_file:
                    line = line.strip()
                    if line == '':
                        continue
                    assert line[:1] == ':'
                    assert len(line) >= 11
                    count = int(line[1:3], 16)
                    addr = int(line[3:7], 16)
                    rectype = int(line[7:9], 16)
                    hex_data = line[9:-2]
                    assert len(hex_data) == count * 2, f"count={count:x} addr={addr:x} rectype={rectype:x} line={line}"
                    data = bytes.fromhex(hex_data)
                    assert len(data) == count
                    checksum = int(line[-2:], 16)
                    if rectype == 0x00: # Data
                        decoded[offset + addr] = data
                    elif rectype == 0x01: # End Of File
                        assert count == 0
                        break
                    elif rectype == 0x02: # Extended Segment Address
                        assert count == 0
                        offset = int(hex_data, 16) * 16
                    elif rectype == 0x03: # Start Segment Address
                        assert count == 4
                        decoded['.text-start'] = int(hex_data[:4], 16)
                        decoded['.pc-start'] = int(hex_data[4:])
                    elif rectype == 0x04: # Extended Linear Address
                        assert count == 2
                        offset = (offset & 0xffff) | int(hex_data, 16) << 16
                    elif rectype == 0x05: # Start Linear Address
                        assert count == 4
                        decoded['.pc-start'] = int(hex_data, 16)

                # Sort and merge data
                data_segs = [k for k in decoded if isinstance(k, int)]
                data_segs.sort()
                prev_addr = None
                data_dict = {}
                for addr in data_segs:
                    data_chunk = decoded[addr]
                    assert isinstance(data_chunk, bytes)
                    if prev_addr is not None and prev_addr + len(data_dict[prev_addr]) >= addr:
                        data_dict[prev_addr] = data_dict[prev_addr][:addr - prev_addr] + data_chunk
                    else:
                        data_dict[addr] = data_chunk
                        prev_addr = addr

                jbin_file.write('{\n')
                pc_start = decoded['.pc-start']
                assert isinstance(pc_start, int)
                jbin_file.write(f'\t"pc-start": "0x{pc_start:x}",\n')
                if '.text-start' in decoded:
                    text_start = decoded['.text-start']
                    assert isinstance(text_start, int)
                    jbin_file.write(f'\t"text-start": "0x{text_start:x}",\n')
                jbin_file.write('\t"data":{\n')
                first = True
                for addr in data_dict:
                    if not first:
                        jbin_file.write(',\n')
                    data_chunk = data_dict[addr]
                    assert isinstance(data_chunk, bytes)
                    jbin_file.write(f'\t\t"0x{addr:08x}":"b64:{_b64.b64encode(data_chunk).decode()}"')
                    first = False
                jbin_file.write('\n\t}\n')
                jbin_file.write('}\n')
        except:
            jbin_path.unlink()
            raise
    return _async.SyncTask(run).as_async
