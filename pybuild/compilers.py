import mypycheck as _chk; _chk.check(__file__)

import asyncfn as _async
import subprocess as _sp
import typing as _t
import base64 as _b64

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

def run_hex_build(compiler: str, args: _t.Sequence[str], exe_path: _Path, hex_path: _Path) -> None:
    cmd = [compiler]
    cmd += args
    cmd += ['-O', 'ihex', str(exe_path), str(hex_path)]
    _sp.check_output(args=cmd, encoding='utf-8', stderr=_sp.PIPE)

def run_jbin_build(hex_path: _Path, jbin_path: _Path) -> None:
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
