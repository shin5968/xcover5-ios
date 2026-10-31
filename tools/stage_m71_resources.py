"""Stage hash-pinned framework Info.plist placeholders; original bytes stay local."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,sys
from stage_m63_resources import safe_path
CONFIG=Path(__file__).resolve().parents[1]/'third_party/hackios-ui-bringup/m71'
FILES=json.loads((CONFIG/'FILES.json').read_text())
def validate(name,size,digest):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or str(p)!=name or not name.startswith(('System/Library/Frameworks/','System/Library/PrivateFrameworks/')) or p.name!='Info.plist':
  raise ValueError('invalid M71 resource path: '+name)
 if not isinstance(size,int) or not 0<size<=1048576 or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
  raise ValueError('invalid M71 resource metadata')
for name,(size,digest) in FILES.items():validate(name,size,digest)
def placeholder(name):return hashlib.shake_256(('XCOVER5 M71 LOCAL BUNDLE '+name).encode()).digest(FILES[name][0])
def stage(root):
 # Check the complete write set before creating any new resource.
 for name in FILES:
  p=safe_path(root,'/'+name)
  if p.exists() or p.is_symlink():raise ValueError('M71 existing resource: '+name)
 for name in sorted(FILES):
  p=safe_path(root,'/'+name);missing=[];parent=p.parent
  while not parent.exists():missing.append(parent);parent=parent.parent
  for d in reversed(missing):d.mkdir();d.chmod(0o755);os.chown(d,0,0)
  p.write_bytes(placeholder(name));p.chmod(0o644);os.chown(p,0,0)
 print('M71 framework metadata placeholders',len(FILES),'bytes',sum(x[0] for x in FILES.values()))
def inject(image,source):
 # Validate all sources and all placeholder occurrences before substitutions.
 replacements=[]
 for name,(size,digest) in FILES.items():
  data=(source/name).read_bytes();assert len(data)==size and hashlib.sha256(data).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,'missing/duplicate/fragmented M71 placeholder: '+name
  replacements.append((stub,data))
 for stub,data in replacements:image=image.replace(stub,data,1)
 return image
if __name__=='__main__':stage(Path(sys.argv[1]))
