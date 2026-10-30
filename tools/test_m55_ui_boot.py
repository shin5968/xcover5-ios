"""Validate real job identities/services and fail-closed local byte injection."""
from pathlib import Path
import hashlib,plistlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage_ui_boot as ui
r=Path(__file__).resolve().parents[1]
for label in ('com.apple.SpringBoard','com.apple.backboardd'):
 original=plistlib.loads((r/'tools/ui-boot-jobs'/(label+'.plist')).read_bytes());job=ui.job(original)
 assert job['Label']==label and job['UserName']=='mobile'
 assert job['ProgramArguments']==original['ProgramArguments'] and job['MachServices']==original['MachServices']
 assert job['RunAtLoad'] and job['KeepAlive'] is False
 assert job['StandardErrorPath']==job['StandardOutPath']=='/dev/console'
 assert not any(k in job for k in ('EmbeddedHomeScreen','LimitLoadFromHardware','_AdditionalProperties','_LimitLoadFromClarityMode'))
 assert plistlib.loads(plistlib.dumps(job))==job
for name,(size,_) in ui.FILES.items():assert len(ui.placeholder(name))==size
# Test actual injector with owned stand-in bytes, no Apple executable in CI.
import tempfile
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);original=ui.FILES
 try:
  payload=b'owned-ui-test';ui.FILES={'native':(len(payload),hashlib.sha256(payload).hexdigest())}
  (root/'native').write_bytes(payload);stub=ui.placeholder('native')
  assert ui.inject(b'prefix'+stub+b'suffix',root)==b'prefix'+payload+b'suffix'
  for image,b in [(b'no placeholder',payload),(stub+stub,payload),(stub,b'bad')]:
   (root/'native').write_bytes(b)
   try:ui.inject(image,root)
   except AssertionError:pass
   else:raise AssertionError('bad byte source/placeholder accepted')
 finally:ui.FILES=original
source=(r/'tools/ui-boot-observer.c').read_text()
assert 'return 77;' in source and 'not UI readiness or lock-screen success' in source
assert 'system(' not in source and 'posix_spawn' not in source and 'kill(' not in source
print('M55 original mobile identities/service names, single-start console jobs, deterministic placeholders and fail-closed exact-byte injector PASS; observer does not launch/kill or claim UI ready')
