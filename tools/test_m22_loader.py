#!/usr/bin/env python3
"""M22 image structure and actual loader instruction tests with simulated XNU.
Usage: test_m22_loader.py APP_MACHO LOADER_MACHO
No test here proves that XNU accepts the images; real device logs must do that.
"""
import struct
import sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR
from unicorn.arm64_const import *

def commands(b):
    h = struct.unpack_from('<8I', b)
    assert h[:3] == (0xfeedfacf, 0x100000c, 0)
    o, result = 32, []
    for _ in range(h[4]):
        c, n = struct.unpack_from('<II', b, o)
        assert n >= 8 and n % 8 == 0 and o+n <= 32+h[5]
        result.append((c, o, b[o:o+n])); o += n
    assert o == 32+h[5] and o <= 1024
    return h, result

def validate(app, loader):
    h, ac = commands(app)
    assert h[3] == 2 and h[6] == 0x200005
    assert not any(c in (5, 0xc, 0x80000018) for c, _, _ in ac)
    load = [d for c, _, d in ac if c == 0xe]
    assert len(load) == 1 and load[0][12:].split(b'\0')[0] == b'/emmc/usr/lib/m22-loader'
    main = [d for c, _, d in ac if c == 0x80000028]
    assert len(main) == 1 and struct.unpack_from('<Q', main[0], 8)[0] == 1024
    h, lc = commands(loader)
    assert h[3] == 7 and not any(c in (0xe, 0xc, 0x80000028) for c, _, _ in lc)
    text = [d for c, _, d in lc if c == 0x19 and d[8:14] == b'__TEXT']
    assert len(text) == 1 and struct.unpack_from('<Q', text[0], 24)[0] == 0
    thread = [d for c, _, d in lc if c == 5]
    assert len(thread) == 1
    entry = struct.unpack_from('<Q', thread[0], 16+32*8)[0]
    assert entry == 1024
    return ac, entry

def prepare(u, app, loader, mode='valid', appbase=0x400000, loaderbase=0x500000):
    ac, entry = validate(app, loader)
    app = bytearray(app)
    mainoff = next(o for c, o, _ in ac if c == 0x80000028)
    if mode == 'magic': app[0] ^= 1
    if mode == 'cpu': app[4] ^= 1
    if mode == 'filetype': struct.pack_into('<I', app, 12, 7)
    if mode == 'count': struct.pack_into('<I', app, 16, 17)
    if mode == 'size': struct.pack_into('<I', app, 20, 4096)
    if mode == 'cmdsize': struct.pack_into('<I', app, 36, 7)
    if mode == 'entry_bounds': struct.pack_into('<Q', app, mainoff+8, 0x4000)
    if mode == 'entry_align': struct.pack_into('<Q', app, mainoff+8, 1025)
    if mode == 'missing_main': struct.pack_into('<I', app, mainoff, 0)
    for base, data in [(appbase, app), (loaderbase, loader)]:
        u.mem_map(base, 0x10000)
        u.mem_write(base, bytes(data))
        u.mem_protect(base, 0x10000, 5)
    # Deliberately 8-byte aligned: matches the extra header pointer XNU pushes.
    stack = 0x21ff88
    u.mem_write(stack, struct.pack('<7Q', appbase, 2 if mode == 'argc' else 1,
                                  0x210000, 0, 0, 0, 0))
    u.mem_write(0x210000, b'/emmc/sbin/m22-probe\0')
    u.reg_write(UC_ARM64_REG_SP, stack)
    return loaderbase+entry

def check(app, loader, mode, appbase, loaderbase):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(0x200000, 0x20000)
    pc = prepare(u, app, loader, mode, appbase, loaderbase)
    result, output = [], []
    def trap(uc, intr, _):
        n = u.reg_read(UC_ARM64_REG_X16)
        a = [u.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)]
        value = 0
        if n == 5:
            name = bytes(u.mem_read(a[0], 64)).split(b'\0')[0]
            assert name in (b'/dev/console', b'/emmc/m20-proof.txt')
            assert a[1] == (2 if name == b'/dev/console' else 0)
            value = 3 if name == b'/dev/console' else 6
        elif n == 4:
            assert a[0] == 3
            output.append(bytes(u.mem_read(a[1], a[2])).decode()); value = a[2]
        elif n == 3:
            assert a[0] == 6 and a[2] == 128
            data = b'XCOVER5 M20 eMMC file read verified\n'
            u.mem_write(a[1], data); value = len(data)
        elif n == 6: pass
        elif n == 20: value = 17
        elif n == 1:
            result.append(a[0]); u.emu_stop()
        else: raise AssertionError(n)
        u.reg_write(UC_ARM64_REG_X0, value)
        u.reg_write(UC_ARM64_REG_NZCV, u.reg_read(UC_ARM64_REG_NZCV) & ~(1 << 29))
    u.hook_add(UC_HOOK_INTR, trap)
    u.emu_start(pc, 0x900000, count=100000)
    assert result == [43 if mode == 'valid' else 112], (mode, result, output)
    if mode == 'valid':
        assert len(output) == 2 and 'LOADER PASS' in output[0] and 'CHILD PASS' in output[1]
    else: assert not output
    print(mode, hex(appbase), hex(loaderbase), 'PASS')

if __name__ == '__main__':
    app, loader = (Path(p).read_bytes() for p in sys.argv[1:])
    for a, l in [(0x400000,0x500000),(0x640000,0x480000),(0x780000,0x840000)]:
        check(app, loader, 'valid', a, l)
    for mode in ['magic','cpu','filetype','count','size','cmdsize','entry_bounds','entry_align','missing_main','argc']:
        check(app, loader, mode, 0x400000, 0x500000)
