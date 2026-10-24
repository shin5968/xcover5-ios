#!/usr/bin/env python3
"""M26 own restricted dylib with two real nlist_64 external section symbols.
Uses LC_SYMTAB, not dyld export tries/chained fixups/shared caches.
"""
import struct,sys
from pathlib import Path
import mkinit as m

def build():
    limit=0x9000
    sigsize=len(m.code_signature(bytes(limit),limit,m.SEG,exec_flags=0))
    strings=b'\0_m26_decoy\0_m26_answer\0'
    # String index is computed rather than relying on the preceding name length.
    symbols=struct.pack('<IBBHQ',1,0xf,1,0,m.BASE+1024)+struct.pack('<IBBHQ',strings.index(b'_m26_answer'),0xf,1,0,m.BASE+1040)
    section=struct.pack('<16s16sQQIIIIIIII',b'__text',b'__TEXT',m.BASE+1024,24,1024,2,0,0,m.S_ATTR_CODE,0,0,0)
    name=b'/emmc/usr/lib/libm26.dylib\0'; n=(24+len(name)+7)&~7
    cmds=[m.segment('__TEXT',m.BASE,m.SEG,0,m.SEG,5,[section]),
          m.segment('__DATA',m.BASE+m.SEG,m.SEG,m.SEG,m.SEG,3),
          m.segment('__LINKEDIT',m.BASE+0x8000,m.SEG,0x8000,0x1000+sigsize,1),
          struct.pack('<6I',0xd,n,24,0,0x10000,0x10000)+name+bytes(n-24-len(name)),
          struct.pack('<6I',2,24,0x8000,2,0x8020,len(strings)),
          struct.pack('<4I',0x1d,16,limit,sigsize)]
    commands=b''.join(cmds)
    header=struct.pack('<8I',m.MH_MAGIC_64,m.CPU_TYPE_ARM64,0,6,len(cmds),len(commands),0x85,0)
    image=bytearray(limit); image[:len(header+commands)]=header+commands
    struct.pack_into('<II',image,1024,0x52800c60,0xd65f03c0) # decoy returns99
    struct.pack_into('<II',image,1040,0x528005e0,0xd65f03c0) # answer returns47
    image[0x8000:0x8020]=symbols
    image[0x8020:0x8020+len(strings)]=strings
    return bytes(image)+m.code_signature(bytes(image),limit,m.SEG,exec_flags=0)

if __name__=='__main__': Path(sys.argv[1]).write_bytes(build())
