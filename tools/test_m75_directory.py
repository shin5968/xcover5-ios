"""Actual fdopendir/readdir preflight with two real dropped identities on host."""
from pathlib import Path
import ast,os,subprocess,tempfile
from stage_m74_var import stage
R=Path(__file__).resolve().parents[1]
assert os.geteuid()==0
tree=ast.parse((R/'tools/test_m74_var.py').read_text())
host=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='host' for t in n.targets))
insert='''
#include <dirent.h>
static DIR *test_fdopendir(int fd){if(!strcmp(test_mode,"fdopenfail")){errno=EIO;return NULL;}return fdopendir(fd);}
static struct dirent *test_readdir(DIR*d){if(!strcmp(test_mode,"readdirfail")){errno=EINVAL;return NULL;}return readdir(d);}
#define fdopendir test_fdopendir
#define readdir test_readdir
#include "m75-dir-proof.h"
#undef fdopendir
#undef readdir
'''
host=host.replace('int main(int argc,char **argv){',insert+'\nint main(int argc,char **argv){')
host=host.replace('int rc=xc74_prepare();','int rc=xc74_prepare();if(!rc)rc=xc75_dir_proof();')
with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
 d=Path(tmp);d.chmod(0o755)
 for name in ['m74-var-init.c','m75-dir-proof.h']:(d/name).write_bytes((R/'tools'/name).read_bytes())
 (d/'host.c').write_text(host)
 subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'host.c'),'-o',str(d/'test')],check=True)
 for mode in ['normal','short','fdopenfail','readdirfail']:
  root=d/mode
  for name,uid,gid,bits in [('private/var',0,0,0o755),('private/var/run',0,0,0o755),('private/var/db',0,0,0o755),('private/var/db/diagnostics',272,272,0o751),('private/var/mobile',501,501,0o711),('private/var/mobile/Library',501,501,0o711),('private/var/mobile/Library/FrontBoard',501,501,0o700)]:
   p=root/name;p.mkdir(parents=True,exist_ok=True);os.chown(p,uid,gid);p.chmod(bits)
  (root/'tmp').symlink_to('private/tmp');stage(root)
  p=subprocess.run([str(d/'test'),str(root),mode],capture_output=True,text=True)
  receipt=root/'private/var/run/xcover-m75-boot-proof.txt'
  if mode in ['normal','short']:
   assert p.returncode==0,p.stdout+p.stderr
   assert 'uid=272 entries=2 errno=0' in p.stdout and 'uid=501 entries=2 errno=0' in p.stdout,p.stdout
   assert receipt.is_file() and 'logd_dir_status=0 mobile_dir_status=0' in receipt.read_text()
   st=receipt.stat();assert (st.st_uid,st.st_gid,st.st_mode&0o7777)==(0,0,0o644)
  else:assert p.returncode==1 and not receipt.exists(),p.stdout+p.stderr
  print('M75 actual native-directory proof',mode,'PASS',flush=True)
print('M75 real fdopendir/readdir under UID272/501 and failed-call handoff stop PASS; host filesystem, not device RAMFS')
