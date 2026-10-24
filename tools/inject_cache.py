#!/usr/bin/env python3
"""Inject locally held original cache into a fresh synthetic HFS FILE.
Never writes an input, block device, partition or remote service.
Usage: TEMPLATE SOURCE_DIRECTORY OUTPUT
Rejects fragmented placeholders; independent HFS extraction is required afterward.
"""
import hashlib,json,mmap,shutil,sys
from pathlib import Path
from cache_placeholders import token,block,LAYOUT
CHUNK=1024*1024
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while b:=f.read(CHUNK):h.update(b)
 return h.hexdigest()
def inject(template,source,out):
 assert template.is_file() and template.stat().st_size==3*1024**3
 assert not out.exists(), 'refuse overwrite'
 items=json.loads(LAYOUT.read_text());assert len(items)==43
 for item in items:
  p=source/item['file'];assert p.is_file() and p.stat().st_size==item['size']
  assert digest(p)==item['sha256'],p
 print('All 43 original SHA256 values verified',flush=True)
 spans=[]
 with template.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
  assert m[1024:1028]==b'HX\0\5'
  by_token={token(item['file']):item for item in items}
  prefix=b'XCOVER5-M28-PLACEHOLDER\0';cursor=0;seen=set()
  while (pos:=m.find(prefix,cursor))>=0:
   t=m[pos:pos+len(prefix)+32];assert t in by_token, 'unknown placeholder'
   item=by_token[t];n=item['size'];assert item['file'] not in seen, 'duplicate placeholder'
   assert pos%4096==0 and pos+n<=len(m)
   pattern=block(item['file'])*256
   for offset in range(0,n,CHUNK):
    length=min(CHUNK,n-offset);assert m[pos+offset:pos+offset+length]==pattern[:length],('fragmented placeholder',item['file'],offset)
   spans.append((pos,pos+n,item));seen.add(item['file']);cursor=pos+n
  assert len(seen)==43, 'missing cache placeholder'
  ordered=sorted(spans)
  assert all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:]))
 template_hash=digest(template)
 with template.open('rb') as f,out.open('xb') as dst:shutil.copyfileobj(f,dst,CHUNK)
 with out.open('r+b') as dst:
  for start,end,item in spans:
   dst.seek(start)
   with (source/item['file']).open('rb') as f:shutil.copyfileobj(f,dst,CHUNK)
 with template.open('rb') as a,out.open('rb') as b:
  cursor=0
  for start,end,item in sorted(spans):
   while cursor<start:
    n=min(CHUNK,start-cursor);assert a.read(n)==b.read(n);cursor+=n
   h=hashlib.sha256();a.seek(end)
   while cursor<end:
    n=min(CHUNK,end-cursor);h.update(b.read(n));cursor+=n
   assert h.hexdigest()==item['sha256']
  while aa:=a.read(CHUNK):assert aa==b.read(len(aa))
  assert not b.read(1)
 report={'template_sha256':template_hash,'image_sha256':digest(out),'size':out.stat().st_size,'files':[dict(item,offset=start) for start,end,item in spans]}
 out.with_suffix('.verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Only expected file bytes replaced; image SHA256',report['image_sha256'],flush=True)
if __name__=='__main__':inject(*(Path(p) for p in sys.argv[1:4]))
