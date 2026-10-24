#!/usr/bin/env python3
"""Stock-matched Samsung LZ4 framing for an already verified Android sparse FILE.
Usage: SPARSE_FILE NEW_OUTPUT.lz4
No device access. Independently simg2img and compare raw SHA256 before using.
"""
import hashlib,struct,sys,lz4.frame
from pathlib import Path
src,out=map(Path,sys.argv[1:]);assert src.is_file() and not out.exists()
with src.open('rb') as f:
 h=f.read(28);magic,major,minor,fh,ch,bs,blocks,chunks,crc=struct.unpack('<IHHHHIIII',h)
 assert (magic,major,minor,fh,ch,bs,blocks)==(0xed26ff3a,1,0,28,12,4096,786432)
 # DONT_CARE could leave stale bytes on real media: permit only explicit RAW/FILL.
 count=0;types={}
 for _ in range(chunks):
  kind,reserved,n,total=struct.unpack('<HHII',f.read(12));assert reserved==0
  assert kind in (0xcac1,0xcac2) and n>0,(kind,n)
  assert total==(12+n*bs if kind==0xcac1 else 16)
  f.seek(total-12,1);count+=n;types[kind]=types.get(kind,0)+1
 assert count==blocks and f.tell()==src.stat().st_size
print('Sparse structure, explicit block coverage, RAW/FILL only verified:',types,flush=True)
enc=lz4.frame.LZ4FrameCompressor(block_size=lz4.frame.BLOCKSIZE_MAX1MB,block_linked=False,content_checksum=True,block_checksum=False,compression_level=0)
original=hashlib.sha256()
with src.open('rb') as f,out.open('xb') as dst:
 dst.write(enc.begin(source_size=src.stat().st_size))
 while b:=f.read(1024*1024):original.update(b);dst.write(enc.compress(b))
 dst.write(enc.flush())
with out.open('rb') as f:info=lz4.frame.get_frame_info(f.read(64))
assert info['block_size']==1048576 and not info['block_linked'] and info['content_checksum'] and not info['block_checksum'] and info['content_size']==src.stat().st_size
h=hashlib.sha256();size=0
with lz4.frame.open(out,'rb') as f:
 while b:=f.read(1024*1024):h.update(b);size+=len(b)
assert size==src.stat().st_size and h.digest()==original.digest()
print('LZ4 roundtrip SHA256',h.hexdigest(),'compressed bytes',out.stat().st_size,flush=True)
