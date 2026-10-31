"""Read-only original fonts/UI assets on the existing 3GiB cache-volume format."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,sys
from stage_m63_resources import safe_path
from stage_m66_icu import CACHE
CONFIG=Path(__file__).resolve().parents[1]/'third_party/hackios-ui-bringup/m72-cache'
FILES=json.loads((CONFIG/'FILES.json').read_text())
DIRS=json.loads((CONFIG/'DIRS.json').read_text())
LINKS=json.loads((CONFIG/'LINKS.json').read_text())
PREFIX='xcover-resources'
def canonical(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or str(p)!=name or not name.startswith('System/Library/'):
  raise ValueError('invalid cached resource path: '+name)
for name,(size,digest) in FILES.items():
 canonical(name)
 if not isinstance(size,int) or not 0<=size<=256*1024**2 or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('invalid cache metadata')
for name in DIRS:
 if name not in ('System','System/Library'):canonical(name)
for name,target in LINKS.items():
 canonical(name);canonical(target)
 if name!=target or target not in FILES and target not in DIRS:raise ValueError('unbacked resource link')
def block(name):
 token=b'XCOVER5-M72-RESOURCE-PLACEHOLDER\0'+hashlib.sha256(name.encode()).digest()
 return token+bytes(4096-len(token))
def stage_cache(root):
 root=Path(root);target=safe_path(root,'/'+PREFIX)
 if target.exists() or target.is_symlink():raise ValueError('existing cache resource pool')
 target.mkdir();target.chmod(0o755);os.chown(target,0,0)
 for name in sorted(DIRS,key=lambda n:(len(PurePosixPath(n).parts),n)):
  p=target/name;p.mkdir(parents=True,exist_ok=True);p.chmod(0o755);os.chown(p,0,0)
 for name,(size,_) in sorted(FILES.items(),key=lambda item:(-item[1][0],item[0])):
  p=target/name;pattern=block(name)*256
  with p.open('xb') as f:
   for off in range(0,size,len(pattern)):f.write(pattern[:min(len(pattern),size-off)])
  p.chmod(0o444);os.chown(p,0,0)
 for name in sorted(DIRS,key=lambda n:len(PurePosixPath(n).parts),reverse=True):(target/name).chmod(0o555)
 target.chmod(0o555)
 print('M72 cache resource placeholders',len(FILES),'bytes',sum(v[0] for v in FILES.values()))
def stage_root(root):
 root=Path(root)
 for name in LINKS:
  p=safe_path(root,'/'+name)
  if p.exists() or p.is_symlink():raise ValueError('existing resource link path: '+name)
 for name,target in LINKS.items():
  p=safe_path(root,'/'+name);missing=[];parent=p.parent
  while not parent.exists():missing.append(parent);parent=parent.parent
  for directory in reversed(missing):directory.mkdir();directory.chmod(0o755);os.chown(directory,0,0)
  p.symlink_to(CACHE+PREFIX+'/'+target);os.chown(p,0,0,follow_symlinks=False)
 print('M72 read-only resource root links',len(LINKS))
if __name__=='__main__':{'cache':stage_cache,'root':stage_root}[sys.argv[1]](Path(sys.argv[2]))
