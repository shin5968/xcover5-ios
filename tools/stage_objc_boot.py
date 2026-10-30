"""M60 original iOS 16.5 runtime-loaded Objective-C trampoline library.

HackiOS fetch.sh retains cryptex files outside the dyld cache; this library
must exist at its runtime dlopen path. Apple bytes remain local-only.
"""
import hashlib,sys
from pathlib import Path
FILES={'usr/lib/libobjc-trampolines.dylib':(68080,'a5410b215468c275e1f861c7e605f58401e332f7f23765a6e1fbe7391d4f05df')}
def placeholder(name):return hashlib.shake_256(('XCOVER5 M60 LOCAL OBJC '+name).encode()).digest(FILES[name][0])
def inject(image,source):
 for name,(size,digest) in FILES.items():
  b=(source/name).read_bytes();assert len(b)==size and hashlib.sha256(b).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,name;image=image.replace(stub,b,1)
 return image
if __name__=='__main__':
 root=Path(sys.argv[1])
 for name in FILES:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(placeholder(name));p.chmod(0o755)
 print('M60 original Objective-C trampoline placeholder staged; no executable/runtime patching')
