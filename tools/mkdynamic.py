#!/usr/bin/env python3
"""Build M22's no-import Mach-O app and diagnostic MH_DYLINKER.
This tests kernel loader handoff/LC_MAIN, not library binding or Apple dyld.
Usage: mkdynamic.py app|loader OBJECT OUTPUT
"""
import struct
import sys
from pathlib import Path
import mkinit as m

LOADER = b'/emmc/usr/lib/m22-loader\0'

def path_command(cmd, loader=LOADER):
    size = (12 + len(loader) + 7) & ~7
    return struct.pack('<III', cmd, size, 12) + loader + bytes(size-12-len(loader))

def build(obj, kind, loader=LOADER, platform=1, apple_metadata=False):
    assert platform in (1, 2)
    assert kind in ('app', 'loader')
    assert not apple_metadata or kind == 'app'
    code, start = m.text_of(obj)
    assert m.CODE_OFF + len(code) <= m.SEG
    base = m.BASE if kind == 'app' else 0
    sect = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', base+m.CODE_OFF,
                       len(code), m.CODE_OFF, 2, 0, 0, m.S_ATTR_CODE, 0, 0, 0)
    # Empty string table, then 16-byte aligned signature for Apple dyld probes.
    prefix = bytes(16) if apple_metadata else b''
    sig_off = m.SEG + len(prefix)
    sig_size = len(m.code_signature(bytes(sig_off), sig_off, m.SEG))
    cmds = [m.segment('__PAGEZERO', 0, base, 0, 0, 0)] if base else []
    cmds += [m.segment('__TEXT', base, m.SEG, 0, m.SEG, 5, [sect]),
             m.segment('__LINKEDIT', base+m.SEG, m.SEG, m.SEG, len(prefix)+sig_size, 1)]
    if kind == 'app':
        cmds += [path_command(0xe, loader), struct.pack('<IIQQ', 0x80000028, 24, m.CODE_OFF+start, 0)]
    else:
        state = [0]*33
        state[32] = m.CODE_OFF+start
        cmds += [path_command(0xf, loader), struct.pack('<4I33QII', 5, 288, 6, 68, *state, 0, 0)]
    if apple_metadata:
        # No imports or absolute fixups in this syscall-only probe. Explicitly
        # describe empty opcode/symbol tables; absent commands trigger dyld's
        # classic-relocation fallback, which dereferences a missing dynSymTab.
        cmds += [struct.pack('<12I', 0x80000022, 48, *([0]*10)),
                 struct.pack('<6I', 2, 24, m.SEG, 0, m.SEG, 1),
                 struct.pack('<20I', 0xb, 80, *([0]*18))]
    # Existing probes default to macOS. M29 explicitly uses iOS and supplies
    # the matching spawn platform attribute; kernel policy is unchanged.
    cmds += [struct.pack('<6I', 0x32, 24, platform, 0x100000 if platform == 2 else 0x0d0000, 0x100000 if platform == 2 else 0x0d0500, 0),
             struct.pack('<4I', 0x1d, 16, sig_off, sig_size)]
    commands = b''.join(cmds)
    header = struct.pack('<8I', m.MH_MAGIC_64, m.CPU_TYPE_ARM64, 0,
                         2 if kind == 'app' else 7, len(cmds), len(commands),
                         0x200005 if kind == 'app' else 5, 0)
    assert len(header+commands) <= m.CODE_OFF
    image = bytearray(m.SEG)
    image[:len(header+commands)] = header+commands
    image[m.CODE_OFF:m.CODE_OFF+len(code)] = code
    image += prefix
    signature = m.code_signature(bytes(image), sig_off, m.SEG)
    assert len(signature) == sig_size
    return bytes(image)+signature

if __name__ == '__main__':
    kind, obj, out = sys.argv[1:]
    Path(out).write_bytes(build(Path(obj).read_bytes(), kind))
    print(kind, out, Path(out).stat().st_size)
