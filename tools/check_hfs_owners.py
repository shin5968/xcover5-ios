"""Read HFS+ catalog ownership directly, independently of host mount options."""
import struct,sys,json,os
from pathlib import Path
def catalog(path):
 b=Path(path).read_bytes();h=1024;block=struct.unpack_from('>I',b,h+40)[0]
 f=h+272;size=struct.unpack_from('>Q',b,f)[0];parts=[]
 for i in range(8):
  start,count=struct.unpack_from('>II',b,f+16+i*8)
  parts.append(b[start*block:(start+count)*block])
 c=b''.join(parts)[:size];assert len(c)==size,'catalog overflow extents unsupported'
 ns=struct.unpack_from('>H',c,32)[0];rows={}
 for off in range(0,len(c),ns):
  n=c[off:off+ns]
  if len(n)!=ns or n[8]!=255:continue
  count=struct.unpack_from('>H',n,10)[0]
  for i in range(count):
   r=struct.unpack_from('>H',n,ns-2*(i+1))[0];kl=struct.unpack_from('>H',n,r)[0]
   parent,nl=struct.unpack_from('>IH',n,r+2);name=n[r+8:r+8+nl*2].decode('utf-16-be')
   d=r+2+kl;typ=struct.unpack_from('>H',n,d)[0]
   if typ not in (1,2):continue
   ident=struct.unpack_from('>I',n,d+8)[0];uid,gid=struct.unpack_from('>II',n,d+32);mode=struct.unpack_from('>H',n,d+42)[0]
   rows[ident]={'name':name,'parent':parent,'uid':uid,'gid':gid,'mode':oct(mode),'id':ident}
 def full(i):
  row=rows[i]
  return '' if i==2 else full(row['parent'])+'/'+row['name']
 return {full(i):r for i,r in rows.items()}
if __name__=='__main__':
 rows=catalog(sys.argv[1])
 for path,row in rows.items():
  mobile_ui=(os.environ.get('XCOVER_HACKIOS_BOOT')=='1' and path.startswith('/private/var/mobile/Library/')) or os.environ.get('XCOVER_UI_BOOT')=='1' and path in ('/private/var/mobile/Library','/private/var/mobile/Library/Preferences','/private/var/mobile/Library/Caches','/private/var/mobile/Library/SpringBoard')
  expected=(501,501) if path=='/private/var/mobile' or mobile_ui else (0,0)
  assert (row['uid'],row['gid'])==expected,(path,row)
 for path,mode in [('/System',0o40755),('/System/Library',0o40755),('/System/Library/LaunchDaemons',0o40755),('/System/Library/LaunchDaemons/org.xcover5.m35.proof.plist',0o100644),('/sbin/m35-proof',0o100755),('/private/etc/master.passwd',0o100600),('/private/var/mobile',0o40700)]:
  assert int(rows[path]['mode'],8)==mode,(path,rows[path])
 print('Raw HFS ownership and launchd path modes PASS',len(rows),'records')
