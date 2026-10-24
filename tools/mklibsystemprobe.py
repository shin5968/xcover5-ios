#!/usr/bin/env python3
"""M30: explicit libSystem imports, resolved by unmodified Apple dyld.

No Apple bytes, hard-coded runtime addresses, lazy binder or local stubs.
__DATA contains five non-lazy pointers populated by standard bind opcodes.
"""
import struct
import sys
from pathlib import Path
import mkinit as m
from mkdynamic import path_command
from mkappleprobe import LOADER

CODE_OFF = 2048
IMPORTS = (b'_getpid', b'_strlen', b'_memcmp', b'_read', b'_write')

def build_code(code, start=0, imports=IMPORTS):
    assert 1 <= len(imports) <= 16 and len(set(imports)) == len(imports)
    assert start == 0, 'assembly computes DATA relative to _start'
    assert CODE_OFF + len(code) <= m.SEG
    # ordinal 1, pointer type, __DATA (segment index 2), offset zero.
    bind = bytearray(b'\x11\x51\x72\x00')
    for name in imports:
        bind += b'\x40' + name + b'\x00\x90'  # symbol, DO_BIND (advance 8)
    bind += b'\x00'
    linkoff = 2*m.SEG
    link = bytearray(bind)
    link += bytes((-len(link)) % 8)
    symoff = linkoff + len(link)
    strings = bytearray(b'\0')
    for name in imports:
        link += struct.pack('<IBBHQ', len(strings), 1, 0, 0x100, 0)
        strings += name + b'\0'
    stroff = linkoff + len(link)
    link += strings
    link += bytes((-len(link)) % 4)
    indirect = linkoff + len(link)
    link += struct.pack('<%dI' % len(imports), *range(len(imports)))
    link += bytes((-len(link)) % 16)
    sigoff = linkoff + len(link)
    sigsize = len(m.code_signature(bytes(sigoff), sigoff, m.SEG))
    text = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT',
                       m.BASE+CODE_OFF, len(code), CODE_OFF, 2, 0, 0, m.S_ATTR_CODE, 0, 0, 0)
    pointers = struct.pack('<16s16sQQIIIIIIII', b'__nl_symbol_ptr', b'__DATA',
                           m.BASE+m.SEG, 8*len(imports), m.SEG, 3, 0, 0, 6, 0, 0, 0)
    lib = b'/usr/lib/libSystem.B.dylib\0'
    libsize = (24+len(lib)+7)&~7
    dylib = struct.pack('<6I', 0xc, libsize, 24, 0, 0x10000, 0x10000)+lib
    dylib += bytes(libsize-len(dylib))
    dysym = [0]*18
    dysym[5] = len(imports)  # iundefsym=0, nundefsym=5
    dysym[12:14] = [indirect, len(imports)]
    cmds = [m.segment('__PAGEZERO', 0, m.BASE, 0, 0, 0),
            m.segment('__TEXT', m.BASE, m.SEG, 0, m.SEG, 5, [text]),
            m.segment('__DATA', m.BASE+m.SEG, m.SEG, m.SEG, m.SEG, 3, [pointers]),
            m.segment('__LINKEDIT', m.BASE+linkoff, m.SEG, linkoff, len(link)+sigsize, 1),
            path_command(0xe, LOADER), struct.pack('<IIQQ', 0x80000028, 24, CODE_OFF, 0),
            dylib,
            struct.pack('<12I', 0x80000022, 48, 0, 0, linkoff, len(bind), 0, 0, 0, 0, 0, 0),
            struct.pack('<6I', 2, 24, symoff, len(imports), stroff, len(strings)),
            struct.pack('<20I', 0xb, 80, *dysym),
            struct.pack('<6I', 0x32, 24, 2, 0x100000, 0x100000, 0),
            struct.pack('<4I', 0x1d, 16, sigoff, sigsize)]
    commands = b''.join(cmds)
    header = struct.pack('<8I', m.MH_MAGIC_64, m.CPU_TYPE_ARM64, 0, 2,
                         len(cmds), len(commands), 0x200085, 0)
    assert len(header+commands) <= CODE_OFF
    image = bytearray(linkoff)
    image[:len(header+commands)] = header+commands
    image[CODE_OFF:CODE_OFF+len(code)] = code
    image += link
    signature = m.code_signature(bytes(image), sigoff, m.SEG)
    assert len(signature) == sigsize
    return bytes(image)+signature

def build(obj):
    return build_code(*m.text_of(obj))

if __name__ == '__main__':
    Path(sys.argv[2]).write_bytes(build(Path(sys.argv[1]).read_bytes()))
