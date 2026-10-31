"""Preflight, ownership, job activation and local-byte substitution boundaries."""
from pathlib import Path
import hashlib,plistlib,tempfile
from unittest.mock import patch
import stage_m72_resources as m
for name,data in m.jobs().items():
 j=plistlib.loads(data);assert j['MachServices'] and j['ThrottleInterval']==30
 assert not any(k in j for k in ('RunAtLoad','KeepAlive','LaunchEvents'))
 assert j['ProgramArguments'][0].lstrip('/') in m.PROGRAMS
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)/'root';root.mkdir();source=Path(tmp)/'source';source.mkdir()
 with patch.object(m.os,'chown') as owner:m.stage(root)
 for name in m.FILES:
  p=root/name;assert p.read_bytes()==m.placeholder(name)
  assert p.stat().st_mode&0o777==(0o755 if name in m.PROGRAMS else 0o644)
 before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
 try:m.stage(root)
 except ValueError:pass
 else:raise AssertionError('existing resources overwritten')
 assert before=={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
 assert owner.called
 for name in ('../escape','/usr/libexec/configd','System/../escape','usr/libexec/other'):
  try:m.validate(name,1,'0'*64)
  except ValueError:pass
  else:raise AssertionError(name)
 data=b'owned-original';name='usr/libexec/configd'
 with patch.object(m,'FILES',{name:[len(data),hashlib.sha256(data).hexdigest()]}):
  p=source/name;p.parent.mkdir(parents=True);p.write_bytes(data)
  stub=m.placeholder(name);image=b'prefix'+stub+b'suffix';assert m.inject(image,source)==b'prefix'+data+b'suffix'
  for bad in (b'no-placeholder',image+stub):
   try:m.inject(bad,source)
   except AssertionError:pass
   else:raise AssertionError('missing/duplicate accepted')
  p.write_bytes(b'wrong-original')
  try:m.inject(image,source)
  except AssertionError:pass
  else:raise AssertionError('wrong source accepted')
print('M72 resources: preflight/no-overwrite, canonical paths, program modes, demand-start jobs, exact local hash and unique placeholder guards PASS')
