"""M62 HackiOS UI graph: stock launchd jobs, local original programs/resources.
Apple executables remain local; CI receives deterministic placeholders only.
"""
from pathlib import Path
import hashlib,json,plistlib,sys,os
CONFIG=Path(__file__).resolve().parents[1]/'third_party/hackios-ui-bringup'
FILES=json.loads((CONFIG/'FILES.json').read_text())
LABELS=json.loads((CONFIG/'JOBS.json').read_text())
def placeholder(name):return hashlib.shake_256(('XCOVER5 M62 LOCAL '+name).encode()).digest(FILES[name][0])
def inject(image,source):
 for name,(size,digest) in FILES.items():
  b=(source/name).read_bytes();assert len(b)==size and hashlib.sha256(b).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,name;image=image.replace(stub,b,1)
 return image
def job(original):
 # HackiOS mkjobs.py: retain original launchd behavior, remove absent device-tree gate.
 from copy import deepcopy
 j=deepcopy(original);j.pop('_LimitLoadToDeviceTree',None)
 j.update(StandardOutPath='/dev/console',StandardErrorPath='/dev/console')
 j.setdefault('EnvironmentVariables',{})['OS_ACTIVITY_DT_MODE']='YES'
 return j
def stage(root):
 for name in FILES:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(placeholder(name));p.chmod(0o644 if name.endswith('.plist') else 0o755)
 for label in LABELS:
  j=job(plistlib.loads((CONFIG/'jobs'/(label+'.plist')).read_bytes()))
  p=root/'System/Library/LaunchDaemons'/(label+'.plist');p.write_bytes(plistlib.dumps(j,fmt=plistlib.FMT_BINARY));p.chmod(0o644)
 for name in ['passwd','master.passwd','group']:
  p=root/'private/etc'/name;p.write_bytes((CONFIG/name).read_bytes());p.chmod(0o600 if name=='master.passwd' else 0o644)
 for name in ['private/var/db/diagnostics','private/var/db/uuidtext','private/var/db/lsd','private/var/db/MobileContainerManager','private/var/run','private/var/log','private/var/containers','private/var/mobile/Library/FrontBoard','private/var/mobile/Library/BackBoard','private/var/mobile/Library/Logs','private/var/mobile/Library/Caches']:
  p=root/name;p.mkdir(parents=True,exist_ok=True);p.chmod(0o700 if name.startswith('private/var/mobile/') else 0o755)
 print('XCOVER5 M62 staged HackiOS UI graph',len(LABELS),'stock jobs',len(FILES),'original local file placeholders')
if __name__=='__main__':stage(Path(sys.argv[1]))
