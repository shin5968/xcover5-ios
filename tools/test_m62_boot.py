"""HackiOS graph integration: stock jobs, complete staged programs/accounts and local injection."""
from pathlib import Path
import sys,plistlib,tempfile,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage_hackios_boot as graph
assert len(graph.LABELS)==21
existing={'usr/sbin/notifyd','usr/sbin/cfprefsd','usr/libexec/backboardd','System/Library/CoreServices/SpringBoard.app/SpringBoard'}
users={line.split(':')[0] for line in (graph.CONFIG/'passwd').read_text().splitlines() if line and not line.startswith('#')}
for name in ('passwd','master.passwd','group'):
 for line in (graph.CONFIG/name).read_text().splitlines():
  if line and not line.startswith('#'):assert line.split(':')[1]=='*'
for label in graph.LABELS:
 original=plistlib.loads((graph.CONFIG/'jobs'/(label+'.plist')).read_bytes());j=graph.job(original)
 assert j['Label']==label and j.get('UserName','root') in users
 assert (j.get('Program') or j['ProgramArguments'][0]).lstrip('/') in set(graph.FILES)|existing
 assert j.get('MachServices')==original.get('MachServices')
 assert j.get('KeepAlive')==original.get('KeepAlive') and j.get('RunAtLoad')==original.get('RunAtLoad')
 assert j['StandardOutPath']==j['StandardErrorPath']=='/dev/console'
 assert '_LimitLoadToDeviceTree' not in j
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);(root/'System/Library/LaunchDaemons').mkdir(parents=True);(root/'private/etc').mkdir(parents=True)
 graph.stage(root)
 for name,(size,_) in graph.FILES.items():assert (root/name).read_bytes()==graph.placeholder(name) and len(graph.placeholder(name))==size
 old=graph.FILES
 try:
  b=b'owned-m62-injection';graph.FILES={'owned':(len(b),hashlib.sha256(b).hexdigest())};(root/'owned').write_bytes(b);stub=graph.placeholder('owned')
  assert graph.inject(b'A'+stub+b'Z',root)==b'A'+b+b'Z'
  for image,data in [(b'missing',b),(stub+stub,b),(stub,b'bad')]:
   (root/'owned').write_bytes(data)
   try:graph.inject(image,root)
   except AssertionError:pass
   else:raise AssertionError('invalid original/placeholder accepted')
 finally:graph.FILES=old
print('M62 21 original job services/startup fields, native-program closure, locked account identities, placeholder staging and rejection tests PASS')
