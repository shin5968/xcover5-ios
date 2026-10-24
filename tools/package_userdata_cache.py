#!/usr/bin/env python3
"""Create LOCAL Odin package overwriting phone boot + userdata when user flashes it.
No device access. Do not include PIT or any other partition.
Usage: BOOT_IMAGE USERDATA_IMAGE NEW_OUTPUT.tar.md5
"""
import hashlib,tarfile,sys,struct
from pathlib import Path
def sha(f,n=None):
 h=hashlib.sha256()
 while n is None or n:
  b=f.read(1024*1024 if n is None else min(n,1024*1024))
  if not b:break
  h.update(b)
  if n is not None:n-=len(b)
 assert n in (None,0)
 return h.hexdigest()
def package(boot,data,out):
 assert out.name.startswith('AP_M28_ERASE_USERDATA') and out.suffix=='.md5' and not out.exists()
 assert boot.is_file() and boot.stat().st_size<44*1024*1024
 with boot.open('rb') as f:
  h=f.read(48);assert h[:8]==b'ANDROID!' and struct.unpack_from('<I',h,40)[0]==2
 assert data.is_file() and data.stat().st_size==3*1024**3
 with data.open('rb') as f:f.seek(1024);assert f.read(4)==b'HX\0\5'
 sources={'boot.img':boot,'userdata.img':data};hashes={}
 with out.open('xb') as dst:
  with tarfile.open(fileobj=dst,mode='w',format=tarfile.GNU_FORMAT) as t:
   for name,p in sources.items():
    info=tarfile.TarInfo(name);info.size=p.stat().st_size;info.mode=0o644
    with p.open('rb') as f:t.addfile(info,f)
 with out.open('rb') as f:
  md5=hashlib.md5()
  while b:=f.read(1024*1024):md5.update(b)
 with out.open('ab') as f:f.write((md5.hexdigest()+'  '+out.name[:-4]+'\n').encode())
 with tarfile.open(out,'r:') as t:
  assert t.getnames()==list(sources)
  for name,p in sources.items():
   with p.open('rb') as f:expected=sha(f)
   with t.extractfile(name) as f:assert sha(f)==expected
   hashes[name]=expected
 with out.open('rb') as f:hashes[out.name]=sha(f)
 out.with_suffix('.sha256.txt').write_text(''.join(f'{v}  {k}\n' for k,v in hashes.items()))
 print('Verified archive contains ONLY boot.img + userdata.img. ANDROID USERDATA WILL BE OVERWRITTEN.')
 print(hashes)
if __name__=='__main__':package(*(Path(p) for p in sys.argv[1:4]))
