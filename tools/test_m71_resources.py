"""Exercise full metadata staging and owned-data source/substitution rejection."""
from pathlib import Path
from unittest.mock import patch
import hashlib,stat,tempfile
import stage_m71_resources as resource
original=resource.FILES
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp)
 with patch('stage_m71_resources.os.chown') as owner:resource.stage(root)
 assert owner.call_count>=len(original)
 for name in original:
  p=root/name;assert p.read_bytes()==resource.placeholder(name)
  assert stat.S_IMODE(p.stat().st_mode)==0o644
 try:resource.stage(root)
 except ValueError:pass
 else:raise AssertionError('existing resource overwritten')
for bad in ['/System/Library/Frameworks/A.framework/Info.plist','System/Library/../Info.plist','System/Library/Frameworks/A.framework/code','private/var/Info.plist']:
 try:resource.validate(bad,10,'0'*64)
 except ValueError:pass
 else:raise AssertionError('invalid path accepted')
try:
 name='System/Library/Frameworks/Owned.framework/Info.plist';data=b'owned bundle metadata'
 resource.FILES={name:[len(data),hashlib.sha256(data).hexdigest()]};stub=resource.placeholder(name)
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);p=root/name;p.parent.mkdir(parents=True);p.write_bytes(data)
  assert resource.inject(b'A'+stub+b'Z',root)==b'A'+data+b'Z'
  for image,body in [(b'missing',data),(stub+stub,data),(stub,b'corrupt')]:
   p.write_bytes(body)
   try:resource.inject(image,root)
   except AssertionError:pass
   else:raise AssertionError('invalid source/substitution accepted')
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);(root/'System').symlink_to(root,target_is_directory=True)
  try:resource.stage(root)
  except ValueError:pass
  else:raise AssertionError('ancestor symlink followed')
finally:resource.FILES=original
print('M71 full staging/modes, overwrite/path/symlink and source/placeholder guards PASS')
