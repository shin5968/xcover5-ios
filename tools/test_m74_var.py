"""Exercise the real var prep body against an owned filesystem and mount shim."""
from pathlib import Path
import hashlib, os, shutil, subprocess, tempfile
from stage_m74_var import stage, SEED
R=Path(__file__).resolve().parents[1]
assert os.geteuid()==0, 'Run this filesystem ownership test as root'
host=r'''
#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
static const char *test_mode;static int mount_calls,write_calls;
static ssize_t test_write(int fd,const void *p,size_t n);
static ssize_t test_read(int fd,void *p,size_t n);
#define write test_write
#define read test_read
#define XC74_HOST_TEST 1
#include "m74-var-init.c"
#undef write
#undef read
static ssize_t test_write(int fd,const void *p,size_t n){
 if(!strcmp(test_mode,"short")){if(!write_calls++){errno=EINTR;return -1;}if(n>17)n=17;}
 return write(fd,p,n);
}
static ssize_t test_read(int fd,void *p,size_t n){if(!strcmp(test_mode,"short")&&n>23)n=23;return read(fd,p,n);}
static int xc74_mount_var(void){
 mount_calls++;
 if(!strcmp(test_mode,"mountfail")){errno=EPERM;return -1;}
 char from[2048],to[2048];xc74_path(from,"/private/var");xc74_path(to,"/private/covered-var");
 return rename(from,to)||mkdir(from,0755);
}
static int xc74_space(void){if(!strcmp(test_mode,"nospace")){errno=ENOSPC;return -1;}return 0;}
int main(int argc,char **argv){
 if(argc!=3)return 10;
 xc74_prefix=argv[1];test_mode=argv[2];int rc=xc74_prepare();
 printf("HOST result=%d mount_calls=%d entries=%u\n",rc,mount_calls,xc74_count);
 return rc?1:0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);(d/'m74-var-init.c').write_bytes((R/'tools/m74-var-init.c').read_bytes());(d/'host.c').write_text(host)
    subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'host.c'),'-o',str(d/'test')],check=True)
    def fixture(name):
        root=d/name
        for tail,uid,gid,mode in [('private/var',0,0,0o755),('private/var/mobile',501,501,0o711),('private/var/mobile/Library',501,501,0o711),('private/var/mobile/Library/FrontBoard',501,501,0o700),('private/var/db',0,0,0o755),('private/var/db/diagnostics',272,272,0o755),('private/var/tmp',0,0,0o1777)]:
            p=root/tail;p.mkdir(parents=True,exist_ok=True);p.chmod(mode);os.chown(p,uid,gid)
        data=bytes(range(256))*33
        p=root/'private/var/mobile/Library/FrontBoard/seed';p.write_bytes(data);p.chmod(0o600);os.chown(p,501,501)
        p=root/'private/var/db/diagnostics/.migrated';p.touch();p.chmod(0o644);os.chown(p,272,272)
        (root/'private/var/db/timezone').symlink_to('/usr/share/zoneinfo')
        (root/'tmp').symlink_to('private/tmp')
        stage(root)
        return root,data
    for mode in ['normal','short','mountfail','nospace','traversal','duplicate','blank','nul','truncated','missingfile','linkparent']:
        root,data=fixture(mode);manifest=root/SEED.lstrip('/')/'manifest.tsv'
        text=manifest.read_text()
        if mode=='traversal':text=text.replace('/private/var/mobile/Library/FrontBoard/seed','/private/var/../escape')
        if mode=='duplicate':text+=text.splitlines()[0]+'\n'
        if mode=='blank':text=text.replace('\n','\n\n',1)
        if mode=='nul':text=text.replace('\n','\0\n',1)
        if mode=='truncated':text=text[:-1]
        if mode=='linkparent':text=text.replace('d\t501\t501\t700\t/private/var/mobile/Library/FrontBoard','l\t501\t501\t755\t/private/var/mobile/Library/FrontBoard\t/escape')
        manifest.write_text(text)
        if mode=='missingfile':next((root/SEED.lstrip('/')/'files').iterdir()).unlink()
        p=subprocess.run([str(d/'test'),str(root),mode],capture_output=True,text=True)
        if mode in ['normal','short']:
            assert p.returncode==0,p.stdout+p.stderr
            for name,uid,gid,bits in [('mobile',501,501,0o711),('mobile/Library/FrontBoard',501,501,0o700),('db/diagnostics',272,272,0o755),('tmp',0,0,0o1777)]:
                st=(root/'private/var'/name).stat();assert (st.st_uid,st.st_gid,st.st_mode&0o7777)==(uid,gid,bits)
            assert (root/'private/var/mobile/Library/FrontBoard/seed').read_bytes()==data
            assert os.readlink(root/'private/var/db/timezone')=='/usr/share/zoneinfo'
            assert os.readlink(root/'tmp')=='private/var/tmp'
        else:
            assert p.returncode==1,p.stdout+p.stderr
            if mode not in ['mountfail','nospace']:assert 'mount_calls=0' in p.stdout,p.stdout
        print('M74 actual prep',mode,'PASS',flush=True)
print('M74 real filesystem seed/mixed ownership/symlinks/short I/O/preflight/failure-stop PASS; native RAMFS not executed on host')
