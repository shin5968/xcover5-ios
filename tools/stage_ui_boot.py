"""M55 bounded real UI launch jobs; Apple bytes injected only locally after CI."""
import hashlib,plistlib,sys
from pathlib import Path
FILES={
 'usr/libexec/backboardd':(1182960,'686f26a6a7b749fd0ae30acca704022da8cb6f85b5c39a0e0e09e25ffd00d273'),
 'System/Library/CoreServices/SpringBoard.app/SpringBoard':(112048,'7926a1ba0b115cf45102b2c3d8e4eb7bc9c84bcf70b573d2a798690d9148059c'),
 'System/Library/CoreServices/SpringBoard.app/Info.plist':(4367,'2357c9d12af0d70ec201d5566d093e06da6ab6da3c48374c593cad2663839c7a'),
}
def placeholder(name):return hashlib.shake_256(('XCOVER5 M55 LOCAL UI '+name).encode()).digest(FILES[name][0])
def inject(image,source):
 for name,(size,digest) in FILES.items():
  b=(source/name).read_bytes();assert len(b)==size and hashlib.sha256(b).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,name
  image=image.replace(stub,b,1)
 return image
def job(original):
 # Keep actual launchd-provided identities and service check-in names. Bounded
 # startup experiment omits home-screen/hardware/RunningBoard activation gates.
 keep=('Label','ProgramArguments','UserName','MachServices','EnvironmentVariables','POSIXSpawnType')
 result={k:original[k] for k in keep if k in original}
 assert result['UserName']=='mobile' and result['Label'] in ('com.apple.backboardd','com.apple.SpringBoard')
 result.update(RunAtLoad=True,KeepAlive=False,StandardOutPath='/dev/console',StandardErrorPath='/dev/console')
 from hackios_services import console_job
 return console_job(result,oslog=True)
if __name__=='__main__':
 root=Path(sys.argv[1]);configs=Path(__file__).with_name('ui-boot-jobs')
 for name in FILES:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(placeholder(name));p.chmod(0o644 if name.endswith('.plist') else 0o755)
 for label in ('com.apple.backboardd','com.apple.SpringBoard'):
  original=plistlib.loads((configs/(label+'.plist')).read_bytes())
  p=root/'System/Library/LaunchDaemons'/(label+'.plist');p.write_bytes(plistlib.dumps(job(original),fmt=plistlib.FMT_BINARY));p.chmod(0o644)
 for directory in ('private/var/mobile/Library','private/var/mobile/Library/Preferences','private/var/mobile/Library/Caches','private/var/mobile/Library/SpringBoard'):
  p=root/directory;p.mkdir(parents=True,exist_ok=True);p.chmod(0o700)
  import os
  os.chown(p,501,501)
 print('M55 real launchd UI jobs staged: mobile501, original service names, one launch per boot, no success claim')
