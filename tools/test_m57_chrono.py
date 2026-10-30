"""Execute exact Chrono lookup policy with mocked kernel/process/copy services."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0087-xcover5-chrono-service-lookup.patch').read_text()
def added(path):
 chunk=p.split('+++ b/'+path+'\n')[1].split('--- ',1)[0]
 return ''.join(x[1:] for x in chunk.splitlines(True) if x.startswith('+'))
identity=added('bsd/sys/xcover5_chrono_identity.h');policy=added('security/xcover5_chrono_lookup.h')
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'bsd/sys/xcover5_chrono_identity.h').read_text()==identity
 assert (t/'security/xcover5_chrono_lookup.h').read_text()==policy
 s=(t/'security/mac_base.c').read_text();needle='if (error == ENOPOLICY) error = xcover5_chrono_lookup(p,uap->arg);'
 assert s.count(needle)==1 and s.count('#include "xcover5_chrono_lookup.h"')==1
 assert s.index('goto done;')<s.index(needle)
 u=(t/'bsd/kern/ubc_subr.c').read_text();a=u.index('error = mac_vnode_check_signature(');b=u.index('if (error != 0)',a);c=u.index('goto out;',b)
 hook='!ui_identity && platform==2 && (cs_flags&2) && xcover5_chrono_identity(tmp_blob.csb_cdhash)==2'
 assert u.count(hook)==1 and c<u.index(hook)<u.index('tmp_blob.csb_flags = cs_flags;',c)
 if '--source-only' in sys.argv:
  print('M57 actual applied exact headers, fallback-only lookup and post-validation Chrono classification PASS');raise SystemExit(0)
prefix=r'''
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#define ENOPOLICY 103
#define CS_VALID 1U
#define CS_SIGNED 0x20000000U
#define CS_PLATFORM_BINARY 0x04000000U
#define PROC_NULL NULL
typedef uintptr_t user_addr_t;typedef int pid_t;
struct Proc{int pid,uid,parent,bits;unsigned version;uint64_t flags;unsigned char hash[20];};typedef struct Proc*proc_t;
static struct Proc root={.pid=1,.uid=0,.bits=1},app;static proc_t initproc=&root;
static unsigned refs,fault,race;
static int proc_pid(proc_t p){return p->pid;}static int proc_getuid(proc_t p){return p->uid;}
static int proc_ppid(proc_t p){return p->parent;}static int proc_is64bit_data(proc_t p){return p->bits;}
static unsigned proc_pidversion(proc_t p){return p->version;}static uint64_t proc_getcsflags(proc_t p){return p->flags;}
static proc_t proc_find(pid_t pid){if(pid!=6)return NULL;refs++;return &app;}
static void proc_rele(proc_t p){assert(p==&app&&refs==1);refs--;}
static int proc_getcdhash(proc_t p,unsigned char*out){if(fault==4)return EIO;memcpy(out,p->hash,20);if(race)p->version++;return 0;}
static int copyin(user_addr_t p,void*out,size_t n){if(!p||fault==1)return EFAULT;memcpy(out,(void*)p,n);return 0;}
static int copyout(const void*p,user_addr_t out,size_t n){if(!out||fault==3)return EFAULT;memcpy((void*)out,p,n);return 0;}
static int copyinstr(user_addr_t p,char*out,size_t max,size_t*n){if(!p||fault==2)return EFAULT;size_t size=strlen((char*)p)+1;if(size>max)return ENAMETOOLONG;memcpy(out,(void*)p,size);*n=size;return 0;}
'''
test=r'''
struct Args{uint64_t result,pid,operation,filter_type,filter,flags,pidversion;};
static const unsigned char spring[20]={0x45,0x3a,0xe2,0xe6,0x05,0x7a,0xcb,0x2d,0xea,0x0c,0x5a,0xe8,0xba,0x09,0x73,0x07,0x7e,0xa3,0xea,0xb1};
static uint64_t decision;static struct Args a;
static void reset(void){assert(!refs);fault=race=0;app=(struct Proc){.pid=6,.uid=501,.parent=1,.bits=1,.version=17,.flags=CS_VALID|CS_SIGNED|CS_PLATFORM_BINARY};memcpy(app.hash,spring,20);decision=99;a=(struct Args){(uintptr_t)&decision,6,(uintptr_t)"mach-lookup",6,(uintptr_t)"com.apple.chronoservices",0x40000000ULL,17};}
static void rejected(int expected){assert(xcover5_chrono_lookup(&root,(uintptr_t)&a)==expected);assert(!refs&&decision==99);}
int main(void){
 reset();assert(!xcover5_chrono_lookup(&root,(uintptr_t)&a)&&decision==0&&!refs);
 reset();app.uid=0;rejected(ENOPOLICY);reset();app.parent=7;rejected(ENOPOLICY);
 reset();app.bits=0;rejected(ENOPOLICY);reset();app.version++;rejected(ENOPOLICY);
 reset();race=1;rejected(ENOPOLICY);reset();app.hash[0]^=1;rejected(ENOPOLICY);
 for(unsigned bit=0;bit<32;bit++)if((CS_VALID|CS_SIGNED|CS_PLATFORM_BINARY)&(1U<<bit)){reset();app.flags&=~(1U<<bit);rejected(ENOPOLICY);}
 reset();a.filter=(uintptr_t)"com.apple.chrono.widgetcenterconnection";rejected(ENOPOLICY);
 reset();a.filter=(uintptr_t)"com.apple.chronoservices.fake";rejected(ENOPOLICY);
 reset();a.operation=(uintptr_t)"mach-cross-domain-lookup";rejected(ENOPOLICY);
 reset();a.filter_type=7;rejected(ENOPOLICY);reset();a.flags=1;rejected(ENOPOLICY);
 reset();a.pidversion=UINT64_MAX;rejected(ENOPOLICY);reset();a.pid=0;rejected(ENOPOLICY);
 reset();a.pid=7;rejected(ESRCH);
 for(unsigned f=1;f<=4;f++){reset();fault=f;rejected(f==4?ENOPOLICY:EFAULT);}
 reset();struct Proc imposter=root;assert(xcover5_chrono_lookup(&imposter,(uintptr_t)&a)==ENOPOLICY&&decision==99);
 reset();root.uid=501;rejected(ENOPOLICY);root.uid=0;
 for(unsigned bit=0;bit<160;bit++){unsigned char bad[20];memcpy(bad,spring,20);bad[bit/8]^=1U<<(bit%8);assert(!xcover5_chrono_identity(bad));}
 assert(!xcover5_chrono_identity(NULL));return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+identity+''.join(x for x in policy.splitlines(True) if not x.startswith('#include'))+test)
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 result=subprocess.run([str(d/'test')],text=True,capture_output=True);assert result.returncode==0,result.stdout+result.stderr
print('M57 actual policy: exact mobile signed-platform SpringBoard/code hash/version/parent/service only; stale/exec-race/flags/UID/shape/copy failures rejected, refs/output preserved PASS')
