"""Offline regression for Apple-dyld probe metadata. Usage: previous CI out dir."""
import hashlib,struct,sys
from pathlib import Path
import mkdynamic
from mkappleprobe import LOADER
old=Path(sys.argv[1])
# Legacy custom-loader probes must remain byte-identical.
for name,kind,loader in [('m22-probe','app',mkdynamic.LOADER),('m22-loader','loader',mkdynamic.LOADER),('m27-probe','app',LOADER)]:
 assert mkdynamic.build((old/(name+'.o')).read_bytes(),kind,loader)==(old/name).read_bytes(),name
obj=(old/'m29-probe.o').read_bytes()
b=mkdynamic.build(obj,'app',LOADER,platform=2,apple_metadata=True)
prev=(old/'m29-probe').read_bytes()
# Executable instructions and all their PC-relative literals are unchanged.
assert b[1024:16384]==prev[1024:16384]
commands={};segments=[];off=32
for _ in range(struct.unpack_from('<I',b,16)[0]):
 cmd,n=struct.unpack_from('<II',b,off);assert n>=8 and n%8==0
 if cmd==0x19:segments.append(b[off:off+n])
 else:assert cmd not in commands;commands[cmd]=b[off:off+n]
 off+=n
assert off==32+struct.unpack_from('<I',b,20)[0] and off<=1024
assert struct.unpack_from('<I',commands[0x32],8)[0]==2
assert struct.unpack_from('<Q',commands[0x80000028],8)[0]==1024
assert commands[0x80000022][8:]==bytes(40)
assert commands[0xb][8:]==bytes(72)
so,ns,st,ss=struct.unpack_from('<4I',commands[2],8)
assert ns==0 and ss==1 and b[st:st+ss]==bytes(1)
link=next(x for x in segments if x[8:24].rstrip(bytes(1))==b'__LINKEDIT')
vm,vs,fo,fs=struct.unpack_from('<4Q',link,24)
sigo,sigs=struct.unpack_from('<II',commands[0x1d],8)
assert fo<=so<=st and st+ss<=sigo and sigo+sigs==fo+fs==len(b) and fs<=vs
sig=b[sigo:];magic,total,num=struct.unpack_from('>III',sig)
assert (magic,total,num)==(0xfade0cc0,len(sig),1)
cd=sig[struct.unpack_from('>I',sig,16)[0]:]
hasho,ident,special,slots,limit=struct.unpack_from('>5I',cd,16)
assert special==0 and limit==sigo and slots==(limit+4095)//4096
for i in range(slots):assert cd[hasho+32*i:hasho+32*(i+1)]==hashlib.sha256(b[i*4096:min(limit,(i+1)*4096)]).digest()
assert struct.unpack_from('>Q',cd,72)[0]==16384
print('PASS: legacy bytes, unchanged M29 code, bounded load commands, empty dyld/symbol metadata, linkedit containment, every signature page')
if len(sys.argv)>2:Path(sys.argv[2]).write_bytes(b)
