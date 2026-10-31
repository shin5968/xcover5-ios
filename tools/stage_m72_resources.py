"""HackiOS demand-start service policy. CI stores hashes/placeholders, not Apple bytes."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,plistlib,sys
from stage_m63_resources import safe_path
CONFIG=Path(__file__).resolve().parents[1]/'third_party/hackios-ui-bringup/m72'
FILES=json.loads((CONFIG/'FILES.json').read_text())
PROGRAMS={'usr/libexec/configd','System/Library/PrivateFrameworks/FontServices.framework/Support/fontservicesd'}
JOBS={
 'com.apple.configd':dict(ProgramArguments=['/usr/libexec/configd'],POSIXSpawnType='Interactive',
  MachServices={k:True for k in ('com.apple.SystemConfiguration.IPMonitorControl','com.apple.network.IPConfiguration',
  'com.apple.network.EAPOLController','com.apple.SystemConfiguration.DNSConfiguration',
  'com.apple.networking.captivenetworksupport','com.apple.SystemConfiguration.configd.watchdog',
  'com.apple.SystemConfiguration.configd','com.apple.SystemConfiguration.USBDeviceConfig',
  'com.apple.SystemConfiguration.NetworkInformation')}),
 'com.apple.fontservicesd':dict(ProgramArguments=['/System/Library/PrivateFrameworks/FontServices.framework/Support/fontservicesd'],
  UserName='mobile',POSIXSpawnType='Adaptive',EnablePressuredExit=True,EnableTransactions=True,
  MachServices={'com.apple.fontservicesd':True})}
DIRS={
 'Library/Preferences/SystemConfiguration':(0,0,0o755),
 'private/var/run/configd':(0,0,0o755),
 'private/var/mobile/Library/FontRegistry':(501,501,0o700),
 'private/var/mobile/Library/Fonts':(501,501,0o700),
 'private/var/mobile/Library/Caches/com.apple.FontServices':(501,501,0o700)}
def validate(name,size,digest):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or str(p)!=name or not(name in PROGRAMS or name.startswith('System/Library/SystemConfiguration/')):
  raise ValueError('invalid M72 resource path: '+name)
 if not isinstance(size,int) or not 0<size<=1048576 or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
  raise ValueError('invalid M72 metadata')
for name,(size,digest) in FILES.items():validate(name,size,digest)
def placeholder(name):return hashlib.shake_256(('XCOVER5 M72 LOCAL SERVICE '+name).encode()).digest(FILES[name][0])
def jobs():
 result={}
 for label,config in JOBS.items():
  value=dict(config,Label=label,StandardOutPath='/dev/console',StandardErrorPath='/dev/console',ThrottleInterval=30,
   EnvironmentVariables={'OS_ACTIVITY_DT_MODE':'YES'})
  result['System/Library/LaunchDaemons/'+label+'.plist']=plistlib.dumps(value,fmt=plistlib.FMT_BINARY)
 return result
def makedirs(root,name,uid=0,gid=0,mode=0o755):
 p=safe_path(root,'/'+name);missing=[];parent=p
 while not parent.exists():missing.append(parent);parent=parent.parent
 for d in reversed(missing):d.mkdir();d.chmod(0o755);os.chown(d,0,0)
 p.chmod(mode);os.chown(p,uid,gid)
def stage(root):
 root=Path(root);j=jobs()
 for name in list(FILES)+list(j):
  p=safe_path(root,'/'+name)
  if p.exists() or p.is_symlink():raise ValueError('M72 existing resource: '+name)
 for name in DIRS:safe_path(root,'/'+name)
 for name,data in [(n,placeholder(n)) for n in FILES]+list(j.items()):
  p=safe_path(root,'/'+name);makedirs(root,str(PurePosixPath(name).parent))
  p.write_bytes(data);p.chmod(0o755 if name in PROGRAMS else 0o644);os.chown(p,0,0)
 for name,(uid,gid,mode) in DIRS.items():makedirs(root,name,uid,gid,mode)
 print('M72 demand-start configd/fontservicesd, resources',len(FILES),'bytes',sum(v[0] for v in FILES.values()))
def inject(image,source):
 replacements=[]
 for name,(size,digest) in FILES.items():
  data=(Path(source)/name).read_bytes();assert len(data)==size and hashlib.sha256(data).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,'missing/duplicate/fragmented M72 placeholder: '+name
  replacements.append((stub,data))
 for stub,data in replacements:image=image.replace(stub,data,1)
 return image
if __name__=='__main__':stage(Path(sys.argv[1]))
