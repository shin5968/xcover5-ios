"""Actual Chrono job and deterministic local-only exact-byte injection."""
from pathlib import Path
import sys,plistlib,tempfile,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage_chrono_boot as chrono
r=Path(__file__).resolve().parents[1]
original=plistlib.loads((r/'tools/ui-boot-jobs/com.apple.chronod.plist').read_bytes());job=chrono.job(original)
assert job['UserName']=='mobile' and job['ProgramArguments']==original['ProgramArguments']
assert job['MachServices']==original['MachServices'] and job['MachServices']['com.apple.chronoservices'] is True
assert job['RunAtLoad'] is False and job['KeepAlive'] is False
assert job['StandardErrorPath']==job['StandardOutPath']=='/dev/console'
assert 'LaunchEvents' not in job and 'EnablePressuredExit' not in job
assert plistlib.loads(plistlib.dumps(job))==job
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
print('M57 actual demand-start original mobile Chrono job/services and fail-closed exact-byte injection PASS; no fake protocol server')
