#!/usr/bin/env python3
"""Execute raw init .text in Unicorn with mocked XNU syscalls and a sparse disk.
Usage: test_m19_init.py TEXT_BIN BOOT_IMG
Requires unicorn. This tests parsing/control flow, not real hardware or XNU ABI.
"""
import struct, sys, zlib
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR
from unicorn.arm64_const import *

code = Path(sys.argv[1]).read_bytes()
boot = Path(sys.argv[2]).read_bytes()
probe = Path(sys.argv[3]).read_bytes() if len(sys.argv) > 3 else None
dynamic = tuple(Path(p).read_bytes() for p in sys.argv[4:6]) or None
if b'M22 USER PASS' in code: assert dynamic and len(dynamic) == 2
if b'M21 USER PASS' in code:
    assert probe, 'M21 requires probe .text as the third argument'
    from test_m21_exec import child
FIRST, LAST, SECTORS = 0x45000, 0x5afff, 0x747c000

def fixture(mode):
    table = bytearray(16384)
    table[:16] = bytes(range(1, 17))
    struct.pack_into('<QQ', table, 32, FIRST, LAST)
    table[56:66] = 'boot\0'.encode('utf-16le')
    if mode == 'duplicate':
        table[128:256] = table[:128]
    if mode == 'range':
        struct.pack_into('<Q', table, 40, SECTORS)
    h = bytearray(512)
    h[:8] = b'EFI PART'
    struct.pack_into('<II', h, 8, 0x10000, 512)
    struct.pack_into('<QQQQ', h, 24, 1, SECTORS-1, 34, SECTORS-34)
    struct.pack_into('<QIII', h, 72, 2, 128, 128, zlib.crc32(table))
    if mode == 'layout':
        struct.pack_into('<I', h, 80, 0xffffffff)
    struct.pack_into('<I', h, 16, zlib.crc32(h))
    if mode == 'header_crc': h[100] ^= 1
    if mode == 'table_crc': table[100] ^= 1
    mbr = bytearray(512)
    mbr[510:512] = b'\x55\xaa'
    b = bytearray(boot)
    if mode == 'boot_magic': b[0] ^= 1
    if mode == 'payload_bounds': struct.pack_into('<I', b, 16, 0xffffffff)
    if mode == 'kernel_overflow': struct.pack_into('<I', b, 8, 0xffffffff)
    return bytes(mbr+h+table), bytes(b)

def run(mode, expected_stage=None):
    disk, boot_data = fixture(mode)
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(0x100000, 0x10000)
    u.mem_write(0x100000, code)
    u.mem_map(0x200000, 0x20000)
    u.reg_write(UC_ARM64_REG_SP, 0x21fff0)
    output, reads = [], []
    counts = {}
    child_state = {'status': None, 'waits': 0, 'killed': False, 'forks': 0}
    def result(value, error=False):
        u.reg_write(UC_ARM64_REG_X0, value)
        nzcv = u.reg_read(UC_ARM64_REG_NZCV) & ~(1 << 29)
        u.reg_write(UC_ARM64_REG_NZCV, nzcv | ((1 << 29) if error else 0))
    def diskread(off, length):
        reads.append((off, length))
        assert length <= 65536 and not ((off | length) & 511)
        assert off + length <= SECTORS * 512
        counts[off] = counts.get(off, 0) + 1
        if off < len(disk) and off+length <= len(disk):
            data = disk[off:off+length]
        elif off >= FIRST*512 and off+length <= FIRST*512+len(boot_data):
            start = off-FIRST*512
            data = boot_data[start:start+length]
        else:
            raise AssertionError(('unexpected disk access', off, length))
        if mode == 'repeat' and length == 16384 and off >= FIRST*512 and counts[off] == 2:
            data = bytes([data[0]^1])+data[1:]
        return data
    def syscall(uc, intno, _):
        n = u.reg_read(UC_ARM64_REG_X16)
        a = [u.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3)]
        if n == 5:
            name = bytes(u.mem_read(a[0], 64)).split(b'\0')[0]
            if name == b'/dev/console': result(3)
            else:
                assert a[1] == 0
                if name == b'/emmc/m20-proof.txt':
                    result(2, True) if mode == 'm20_open' else result(6)
                else:
                    assert name == b'/dev/xcmmc'
                    result(4)
        elif n == 4:
            assert a[0] == 3, 'no writes to media allowed'
            output.append(bytes(u.mem_read(a[1], a[2])).decode())
            result(a[2])
        elif n == 20: result(1)
        elif n == 167:
            assert bytes(u.mem_read(a[0], 4)) == b'hfs\0'
            assert bytes(u.mem_read(a[1], 6)) == b'/emmc\0'
            assert a[2] == 1
            dev = struct.unpack('<Q', u.mem_read(a[3], 8))[0]
            assert bytes(u.mem_read(dev, 11)) == b'/dev/xchfs\0'
            result(6, True) if mode == 'm20_mount' else result(0)
        elif n == 3 and a[0] == 6:
            data = b'XCOVER5 M20 eMMC file read verified\n'
            if mode == 'm20_short': data = data[:-1]
            if mode == 'm20_content': data = b'!'+data[1:]
            if mode == 'm20_read': result(5, True)
            else:
                u.mem_write(a[1], data)
                result(len(data))
        elif n in (3, 153):
            assert a[0] == 4
            off = a[3] if n == 153 else 0
            if mode == 'pread_error' and n == 153:
                result(5, True)
            else:
                data = diskread(off, a[2])
                if mode == 'short_read' and n == 153: data = data[:-512]
                u.mem_write(a[1], data)
                result(len(data))
        elif n == 6: result(0)
        elif n == 2:
            child_state['forks'] += 1
            prefix = 'm21' if child_state['forks'] == 1 else 'm22'
            child_state['prefix'] = prefix
            child_state['waits'] = 0
            if mode == prefix+'_fork': result(12, True)
            else:
                status, child_output = child(u, code, probe, mode, dynamic if prefix == 'm22' else None)
                output.extend(child_output)
                child_state['status'] = status
                u.reg_write(UC_ARM64_REG_X1, 0)
                result(17)
        elif n == 7:
            assert a[2:] == [1, 0]
            if a[0] == 0xffffffffffffffff:
                assert a[1] == 0
                result(10, True) # alive-loop reaper, no children remaining
            else:
                assert a[0] == 17
                child_state['waits'] += 1
                prefix = child_state['prefix']
                child_state[prefix+'_waits'] = child_state['waits']
                if mode == prefix+'_wait': result(10, True)
                elif mode == prefix+'_timeout': result(0)
                elif mode == prefix+'_eintr' and child_state['waits'] == 1: result(4, True)
                elif child_state['waits'] == 1: result(0) # genuinely exercise polling
                else:
                    status = 9 if mode == prefix+'_signal' else child_state['status']
                    if mode == prefix+'_exit': status = 0
                    u.mem_write(a[1], struct.pack('<I', status))
                    result(17)
        elif n == 37:
            assert a[:3] == [17, 9, 1]
            child_state['killed'] = True
            result(0)
        elif n == 93:
            tv = u.reg_read(UC_ARM64_REG_X4)
            seconds, usec = struct.unpack('<qI', u.mem_read(tv, 12))
            if (seconds, usec) == (0, 100000): result(0)
            else:
                assert seconds == 5
                u.emu_stop()
        else: raise AssertionError(('unexpected syscall', n))
    u.hook_add(UC_HOOK_INTR, syscall)
    u.emu_start(0x100000, 0x100000+len(code), count=20000000)
    out = ''.join(output)
    if mode.startswith(('m21_', 'm22_')):
        label = mode[:3].upper()
        if expected_stage is None:
            assert label+' USER PASS' in out, out
        else:
            assert f'{label} USER FAIL stage={expected_stage:08x}' in out, out
            assert label+' USER PASS' not in out, out
        if mode.endswith('_timeout'):
            assert child_state[mode[:3]+'_waits'] == 100 and child_state['killed']
        print(f'{mode}: checked {label} result, stage={expected_stage}')
    elif mode.startswith('m20_'):
        assert 'M19 USER PASS' in out, out
        assert f'M20 USER FAIL stage={expected_stage:08x}' in out, out
        assert 'M20 USER PASS' not in out, out
        assert 'M21 USER' not in out, out
        print(f'{mode}: correctly rejected at stage {expected_stage}')
    elif expected_stage is None:
        assert 'M19 USER PASS' in out, out
        if b'M20 USER PASS' in code: assert 'M20 USER PASS' in out, out
        if b'M21 USER PASS' in code: assert 'M21 USER PASS' in out, out
        if b'M22 USER PASS' in code: assert 'M22 USER PASS' in out, out
        kernel_size = struct.unpack_from('<I', boot, 8)[0]
        offset = 2048 + ((kernel_size+2047)//2048)*2048
        expected = zlib.crc32(boot[offset:offset+16384])
        assert f'CRC={expected:08x}' in out, out
        print(f'{mode}: PASS, payload CRC={expected:08x}, media reads={len(reads)}')
    else:
        assert f'M19 USER FAIL stage={expected_stage:08x}' in out, out
        assert 'M19 USER PASS' not in out, out
        print(f'{mode}: correctly rejected at stage {expected_stage}')

for mode, stage in [('valid', None), ('header_crc', 3), ('layout', 3),
                    ('table_crc', 4), ('duplicate', 5), ('range', 5),
                    ('boot_magic', 6), ('payload_bounds', 6), ('kernel_overflow', 6),
                    ('repeat', 7), ('short_read', 2), ('pread_error', 2)]:
    run(mode, stage)

if b'M20 USER PASS' in code:
    for mode, stage in [('m20_mount', 21), ('m20_open', 22), ('m20_read', 23), ('m20_short', 24), ('m20_content', 24)]:
        run(mode, stage)

if b'M22 USER PASS' in code:
    for mode, stage in [('m22_fork', 41), ('m22_wait', 42), ('m22_timeout', 44),
                        ('m22_exec_error', 43), ('m22_exit', 43), ('m22_signal', 43),
                        ('m22_eintr', None), ('m22_child_pid', 43), ('m22_child_open', 43),
                        ('m22_child_read', 43), ('m22_child_short', 43),
                        ('m22_child_content', 43), ('m22_child_write', 43)]:
        run(mode, stage)

if b'M21 USER PASS' in code:
    for mode, stage in [('m21_fork', 31), ('m21_wait', 32), ('m21_timeout', 34),
                        ('m21_exec_error', 33), ('m21_exit', 33), ('m21_signal', 33),
                        ('m21_eintr', None), ('m21_child_pid', 33), ('m21_child_open', 33),
                        ('m21_child_read', 33), ('m21_child_short', 33),
                        ('m21_child_content', 33), ('m21_child_write', 33)]:
        run(mode, stage)
