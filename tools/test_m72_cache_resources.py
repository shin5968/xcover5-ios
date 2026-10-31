"""Verify namespace boundaries and linkage without embedding Apple resources."""
from pathlib import Path
from unittest.mock import patch
import tempfile,hashlib
import stage_m72_cache_resources as m
assert sum(v[0] for v in m.FILES.values())<430*1024**2
assert 'System/Library/Fonts/CoreUI/SFUI.ttf' in m.FILES
assert 'System/Library/Fonts/Core/AppleSDGothicNeo.ttc' in m.FILES
assert m.LINKS['System/Library/Fonts']=='System/Library/Fonts'
assert not any(k in m.LINKS for k in ('System/Library/Frameworks','System/Library/PrivateFrameworks'))
for bad in ('/System/Library/Fonts','System/Library/../escape','../../escape'):
 try:m.canonical(bad)
 except ValueError:pass
 else:raise AssertionError(bad)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)/'root';root.mkdir()
 with patch.object(m.os,'chown'):
  m.stage_root(root)
  for name,target in m.LINKS.items():assert (root/name).is_symlink() and str((root/name).readlink())==m.CACHE+m.PREFIX+'/'+target
  before=set(root.rglob('*'))
  try:m.stage_root(root)
  except ValueError:pass
  else:raise AssertionError('overwritten existing link')
  assert set(root.rglob('*'))==before
 cache=Path(tmp)/'cache';cache.mkdir();name='System/Library/Fonts/owned-test.ttf';size=8201
 with patch.object(m,'FILES',{name:[size,hashlib.sha256(b'owned').hexdigest()]}),patch.object(m,'DIRS',['System','System/Library','System/Library/Fonts']),patch.object(m.os,'chown'):
  m.stage_cache(cache);data=(cache/m.PREFIX/name).read_bytes()
  assert len(data)==size and data==(m.block(name)*3)[:size]
  assert (cache/m.PREFIX/name).stat().st_mode&0o777==0o444
  try:m.stage_cache(cache)
  except ValueError:pass
  else:raise AssertionError('overwritten cache pool')
print('M72 fonts/assets: exact read-only cache paths, original framework namespace retained, non-overwrite/preflight, chunk boundaries and resource budget PASS')
