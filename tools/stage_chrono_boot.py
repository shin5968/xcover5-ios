"""M57 demand-start real Chrono service; original Apple bytes stay local."""
import hashlib,plistlib,sys
from pathlib import Path
FILES={
 'System/Library/PrivateFrameworks/ChronoCore.framework/Support/chronod':(65184,'361abe1f4401030c93e8f91aee480606b951a3233a7cfa30de9d9002bc9fa4f0'),
 'System/Library/PrivateFrameworks/ChronoCore.framework/Info.plist':(782,'a63db088397bc2c61e31929f46dcb68d92d41b5bd0f3089179af78e9391d7378'),
}
def placeholder(name):return hashlib.shake_256(('XCOVER5 M57 LOCAL CHRONO '+name).encode()).digest(FILES[name][0])
def inject(image,source):
 for name,(size,digest) in FILES.items():
  b=(source/name).read_bytes();assert len(b)==size and hashlib.sha256(b).hexdigest()==digest,name
  stub=placeholder(name);assert image.count(stub)==1,name;image=image.replace(stub,b,1)
 return image
def job(original):
 assert original['Label']=='com.apple.chronod' and original['UserName']=='mobile'
 keep=('Label','ProgramArguments','UserName','MachServices','POSIXSpawnType')
 result={k:original[k] for k in keep}
 result.update(RunAtLoad=False,KeepAlive=False,StandardOutPath='/dev/console',StandardErrorPath='/dev/console')
 from hackios_services import console_job
 return console_job(result,oslog=True)
if __name__=='__main__':
 root=Path(sys.argv[1])
 for name in FILES:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(placeholder(name));p.chmod(0o644 if name.endswith('.plist') else 0o755)
 original=plistlib.loads(Path(__file__).with_name('ui-boot-jobs').joinpath('com.apple.chronod.plist').read_bytes())
 p=root/'System/Library/LaunchDaemons/com.apple.chronod.plist';p.write_bytes(plistlib.dumps(job(original),fmt=plistlib.FMT_BINARY));p.chmod(0o644)
 print('M57 real chronod job staged: mobile501, original services, demand start, no fake replies/readiness claim')
