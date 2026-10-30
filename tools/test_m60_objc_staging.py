"""Actual local-only original runtime dependency staging, invalid injection rejection."""
from pathlib import Path
import sys,tempfile,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage_objc_boot as chrono
assert list(chrono.FILES)==['usr/lib/libobjc-trampolines.dylib']
for name,(size,_) in chrono.FILES.items():assert len(chrono.placeholder(name))==size
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);old=chrono.FILES
 try:
  b=b'owned-chrono-fixture';chrono.FILES={'native':(len(b),hashlib.sha256(b).hexdigest())};(root/'native').write_bytes(b)
  stub=chrono.placeholder('native');assert chrono.inject(b'A'+stub+b'Z',root)==b'A'+b+b'Z'
  for image,data in [(stub+stub,b),(b'no placeholder',b),(stub,b'bad')]:
   (root/'native').write_bytes(data)
   try:chrono.inject(image,root)
   except AssertionError:pass
   else:raise AssertionError('bad source/placeholder accepted')
 finally:chrono.FILES=old
print('M60 exact original trampoline metadata and fail-closed placeholder injection PASS')
