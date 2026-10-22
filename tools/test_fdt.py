#!/usr/bin/env python3
"""Host checks: gcc -shared -fPIC shim/fdt.c -o shim/out/fdt-host.so."""
import ctypes, struct
from pathlib import Path
lib=ctypes.CDLL(str(Path(__file__).resolve().parent.parent/'shim/out/fdt-host.so'))
f=lib.fdt_chosen_u64; f.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.POINTER(ctypes.c_uint64)]
def u(*v): return struct.pack('>'+'I'*len(v),*v)
def pad(b): return b+b'\0'*(-len(b)%4)
def tree(value):
 names=b'linux,initrd-start\0'
 body=u(1)+pad(b'\0')+u(1)+pad(b'chosen\0')+u(3,len(value),0)+pad(value)+u(2,2,9)
 return bytearray(u(0xd00dfeed,40+len(body)+len(names),40,40+len(body),0,17,16,0,len(names),len(body))+body+names)
def call(blob,expected=None):
 b=ctypes.create_string_buffer(bytes(blob));v=ctypes.c_uint64(0)
 rc=f(b,b'linux,initrd-start',ctypes.byref(v))
 assert rc==(expected is not None),(rc,expected)
 if rc: assert v.value==expected
call(tree(u(0x84080000)),0x84080000)
call(tree(struct.pack('>Q',0x880000000)),0x880000000)
call(tree(b'12345'))
b=tree(u(1));b[0]=0;call(b)
b=tree(u(1));b[8:12]=u(0xfffffff0);call(b)
b=tree(u(1));b[32:36]=u(0xffffffff);call(b)
b=tree(u(1));b[36:40]=u(4);call(b)
b=tree(u(1));b[68:72]=u(0xffffffff);call(b)
print('PASS: 8 FDT host checks (32/64-bit cells, malformed headers/properties)')
