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
                assert name == b'/dev/xcmmc' and a[1] == 0
                result(4)
        elif n == 4:
            assert a[0] == 3, 'no writes to media allowed'
            output.append(bytes(u.mem_read(a[1], a[2])).decode())
            result(a[2])
        elif n == 20: result(1)
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
        elif n == 93: u.emu_stop()
        else: raise AssertionError(('unexpected syscall', n))
    u.hook_add(UC_HOOK_INTR, syscall)
    u.emu_start(0x100000, 0x100000+len(code), count=20000000)
    out = ''.join(output)
    if expected_stage is None:
        assert 'M19 USER PASS' in out, out
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
