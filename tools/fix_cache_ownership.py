#!/usr/bin/env python3
"""Repair ONLY UID/GID fields in the exact verified M28 cache image, into a NEW FILE.
Never opens a device. Source is hash pinned. Catalog layout follows Apple hfs_format.h:
https://github.com/apple-oss-distributions/hfs/blob/main/core/hfs_format.h
Independent full-file HFS extraction must follow before packaging.
"""
import hashlib,json,struct,sys
from pathlib import Path
SOURCE_SHA='8e67208689f579348f5c1803be96e60a17c493a0595c6aab9933b4ba2a9eb400'
SIZE=3*1024**3
CHUNK=1024**2
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(CHUNK):h.update(b)
 return h.hexdigest()
def records(p):
 assert p.is_file() and p.stat().st_size==SIZE
 with p.open('rb') as f:
  f.seek(1024);h=f.read(512);f.seek(SIZE-1024);alternate=f.read(512)
  assert h[:4]==alternate[:4]==b'HX\0\5'
  # Hdiutil backup header has older counters/timestamps; geometry and forks agree.
  assert h[40:48]==alternate[40:48] and h[80:]==alternate[80:]
  assert struct.unpack_from('>I',h,4)[0]&0x2900==0x100
  assert struct.unpack_from('>II',h,40)==(4096,786432)
  size,clump,blocks=struct.unpack_from('>QII',h,272)
  ext=struct.unpack_from('>16I',h,288)
  assert size==blocks*4096 and size<=16*1024**2 and ext[1]==blocks and ext[2:]==(0,)*14
  base=ext[0]*4096;assert 4096<=base and base+size<SIZE-1024
  f.seek(base);cat=f.read(size)
 assert cat[8]==1 and struct.unpack_from('>H',cat,10)[0]==3
 depth,root,leafcount,first,last,ns,keymax,total,free=struct.unpack_from('>HIIIIHHII',cat,14)
 assert ns in (4096,8192,16384,32768) and total*ns==size and free<total
 assert struct.unpack_from('>H',cat,ns-2)[0]==14
 nodeid=first;prev=0;visited=set();result=[];count=0
 while nodeid:
  assert 0<nodeid<total and nodeid not in visited;visited.add(nodeid)
  node=cat[nodeid*ns:(nodeid+1)*ns]
  nxt,back,kind,height,n,res=struct.unpack_from('>IIbBHH',node)
  assert back==prev and kind==-1 and height==1 and res==0 and 0<n<ns//8
  offsets=[struct.unpack_from('>H',node,ns-2*(i+1))[0] for i in range(n+1)]
  assert offsets[0]==14 and all(a<b for a,b in zip(offsets,offsets[1:])) and offsets[-1]<=ns-2*(n+1)
  for start,end in zip(offsets,offsets[1:]):
   kl=struct.unpack_from('>H',node,start)[0];assert kl>=6 and kl%2==0
   parent,nlen=struct.unpack_from('>IH',node,start+2);assert kl==6+2*nlen and nlen<=255
   pos=start+2+kl;assert pos+2<=end
   name=node[start+8:pos].decode('utf-16be');typ=struct.unpack_from('>H',node,pos)[0]
   assert typ in (1,2,3,4)
   if typ in (1,2):
    assert end-pos==(88 if typ==1 else 248)
    uid,gid=struct.unpack_from('>II',node,pos+32);mode=struct.unpack_from('>H',node,pos+42)[0]
    result.append(dict(name=name,parent=parent,kind=typ,uid=uid,gid=gid,mode=mode,offset=base+nodeid*ns+pos+32))
  count+=n;prev=nodeid;nodeid=nxt
 assert prev==last and count==leafcount
 return result
def repair(src,out):
 assert src.resolve()!=out.resolve() and not out.exists() and out.parent.is_dir()
 assert src.is_file() and src.stat().st_size==SIZE and digest(src)==SOURCE_SHA,'unknown source image'
 items=json.loads(Path(__file__).with_name('cache-layout.json').read_text())
 expected={i['file'] for i in items}|{'m28-cache-proof.txt'}
 recs=records(src);targets=[r for r in recs if (r['parent']==2 and r['name'] in expected) or (r['parent']==1 and r['name']=='XCIOSCACHE')]
 assert len(targets)==45 and {r['name'] for r in targets}==expected|{'XCIOSCACHE'}
 for r in targets:
  assert (r['uid'],r['gid'])==(501,20)
  assert (r['kind'],r['mode'])==((1,0o40755) if r['name']=='XCIOSCACHE' else (2,0o100444))
 offsets=sorted(r['offset'] for r in targets);assert len(set(offsets))==45
 hout=hashlib.sha256()
 with src.open('rb') as a,out.open('xb') as b:
  cursor=0
  while block:=a.read(CHUNK):
   patched=bytearray(block)
   for off in offsets:
    if cursor<=off<cursor+len(block):
     assert off+8<=cursor+len(block);patched[off-cursor:off-cursor+8]=bytes(8)
   b.write(patched);hout.update(patched);cursor+=len(block)
 assert cursor==SIZE
 # Full comparison: only the planned eight-byte ownership fields may differ.
 with src.open('rb') as a,out.open('rb') as b:
  cursor=0;diffbytes=0
  while original:=a.read(CHUNK):
   changed=b.read(len(original));expected_block=bytearray(original)
   for off in offsets:
    if cursor<=off<cursor+len(original):expected_block[off-cursor:off-cursor+8]=bytes(8)
   assert changed==expected_block
   diffbytes+=sum(x!=y for x,y in zip(original,changed)) if changed!=original else 0
   cursor+=len(original)
  assert not b.read(1)
 fixed=records(out)
 assert len(fixed)==len(recs)
 for before,after in zip(recs,fixed):
  want=dict(before)
  if before in targets:want.update(uid=0,gid=0)
  assert after==want
 report=dict(source_sha256=SOURCE_SHA,output_sha256=hout.hexdigest(),changed_bytes=diffbytes,records=targets)
 out.with_suffix('.ownership.json').write_text(json.dumps(report,indent=2))
 print('45 ownership records verified; all other bytes unchanged;',diffbytes,'bytes changed',flush=True)
 print('OUTPUT SHA256',hout.hexdigest(),flush=True)
if __name__=='__main__':
 if len(sys.argv)==2:
  r=records(Path(sys.argv[1]));print(json.dumps(r,indent=2))
 else:repair(*(Path(a) for a in sys.argv[1:3]))
