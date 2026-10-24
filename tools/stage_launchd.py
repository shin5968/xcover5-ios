"""Stage only owned code/config plus deterministic non-executable placeholders."""
import hashlib, plistlib, sys
from pathlib import Path
FILES = {
 'sbin/launchd.ios': (525088, '4c61512d19b9a55a6ddad27e23b88fc5008fbf77d0c0b5e6bdd7c7d90cef3e06'),
 'usr/libexec/xpcproxy': (96352, '2d1f607a248961d6a8612aca68a42c57069fa9cf3f5afbee448cf3e70eeb315f'),
}
def placeholder(name):
 return hashlib.shake_256(('XCOVER5 M35 LOCAL ONLY '+name).encode()).digest(FILES[name][0])
def inject(image, sources):
 for name,(size,digest) in FILES.items():
  original=sources[name].read_bytes()
  assert len(original)==size and hashlib.sha256(original).hexdigest()==digest, name
  stub=placeholder(name)
  assert image.count(stub)==1, 'fragmented or missing placeholder: '+name
  image=image.replace(stub,original,1)
 return image
if __name__=='__main__':
 root=Path(sys.argv[1])
 for name in FILES:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(placeholder(name));p.chmod(0o755)
 for name in ['usr/lib','private/var/run','private/var/db','private/var/tmp','private/var/log','private/var/root','private/tmp','etc','System/Library/LaunchDaemons','System/Library/xpc']:
  (root/name).mkdir(parents=True,exist_ok=True)
 for name,target in [('var','private/var'),('tmp','private/tmp'),('usr/lib/dyld','m27-apple-dyld')]:
  (root/name).symlink_to(target)
 (root/'private/tmp').chmod(0o1777)
 (root/'private/var/tmp').chmod(0o1777)
 job={'Label':'org.xcover5.m35.proof','ProgramArguments':['/sbin/m35-proof'],'RunAtLoad':True,'KeepAlive':False,'StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console'}
 (root/'System/Library/LaunchDaemons/org.xcover5.m35.proof.plist').write_bytes(plistlib.dumps(job,fmt=plistlib.FMT_BINARY))
 assert not (root/'System/Library/xpc/launchd.plist').exists()
 print('M35 staged: one proof job; local Apple substitution required')
