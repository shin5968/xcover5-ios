#!/usr/bin/env python3
"""Own M25 restricted Mach-O dylib: RX text, private RW data, one preferred pointer.
No imports, chained fixups or general dyld compatibility are claimed.
"""
import struct, sys
from pathlib import Path
import mkinit as m

def build():
    size = 2*m.SEG
    sig_size = len(m.code_signature(bytes(size), size, m.SEG, exec_flags=0))
    name = b'/emmc/usr/lib/libm25.dylib\0'
    n = (24+len(name)+7)&~7
    cmds = [m.segment('__TEXT', m.BASE, m.SEG, 0, m.SEG, 5),
            m.segment('__DATA', m.BASE+m.SEG, m.SEG, m.SEG, m.SEG, 3),
            m.segment('__LINKEDIT', m.BASE+size, m.SEG, size, sig_size, 1),
            struct.pack('<6I', 0xd, n, 24, 0, 0x10000, 0x10000)+name+bytes(n-24-len(name)),
            struct.pack('<4I', 0x1d, 16, size, sig_size)]
    commands = b''.join(cmds)
    header = struct.pack('<8I', m.MH_MAGIC_64, m.CPU_TYPE_ARM64, 0, 6, len(cmds), len(commands), 0x85, 0)
    image = bytearray(size)
    image[:len(header+commands)] = header+commands
    image[m.CODE_OFF:m.CODE_OFF+8] = struct.pack('<II', 0x528005c0, 0xd65f03c0) # mov w0,46; ret
    struct.pack_into('<Q', image, m.SEG, m.BASE+m.CODE_OFF)
    return bytes(image)+m.code_signature(bytes(image),size,m.SEG,exec_flags=0)

if __name__ == '__main__':
    Path(sys.argv[1]).write_bytes(build())
