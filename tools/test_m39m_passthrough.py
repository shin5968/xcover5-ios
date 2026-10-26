"""Actual corrected M39N header: post-close ABI, scope and failure preservation."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0064-xcover5-preferences-passthrough.patch').read_text()
h=''.join(x[1:] for x in p.split('+++ b/security/xcover5_prefs_passthrough.h\n',1)[1].splitlines(True) if x.startswith('+'))
correction=(r/'xnu/patches/0065-xcover5-preferences-post-close.patch').read_text()
h=''.join(x[1:] for x in correction.splitlines(True) if x.startswith('+') and not x.startswith('+++'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_passthrough.h').read_text()==h
 assert 'error = xcover5_prefs_passthrough(p,uap->arg);' in (t/'security/mac_base.c').read_text()
prefix=r"""
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ENOPOLICY 103
#define user_addr_t uintptr_t
struct proc {unsigned uid;int bits;const char *p_comm;};typedef struct proc *proc_t;
static int fault;
static unsigned proc_getuid(proc_t p){return p->uid;}
static int proc_is64bit_data(proc_t p){return p->bits;}
static int proc_pid(proc_t p){(void)p;return 6;}
static int copyin(user_addr_t a,void *b,size_t n){if(fault||!a)return EFAULT;memcpy(b,(void*)a,n);return 0;}
/* No FD/vnode/path/copyout APIs are provided: their use must fail compilation. */
"""
test=r"""
int main(void){
 struct proc actor={0,1,"m39-probe"};uint64_t a[2]={5,0x102},saved[2];memcpy(saved,a,sizeof(a));
 /* Represents the original caller's descriptor value after close. */
 assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);assert(!memcmp(a,saved,sizeof(a)));
 actor.p_comm="cfprefsd";assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);
 fault=1;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==EFAULT);fault=0;
 assert(xcover5_prefs_passthrough(&actor,0)==EFAULT);
 actor.uid=501;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.uid=0;
 actor.bits=0;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.bits=1;
 actor.p_comm="other";assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.p_comm="m39-probe";
 for(unsigned i=0;i<64;i++){a[1]=0x102ULL^(1ULL<<i);assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);}a[1]=0x102;
 a[0]=UINT64_MAX;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);
 a[0]=0x80000000ULL;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);
 a[0]=0x100000005ULL;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);
 a[0]=0;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);
 a[0]=0x7fffffffULL;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);
 puts("M39N actual header: post-close ABI, scope, exact flags, copy faults, no FD lookup or output writes PASS (host only)");
}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+h+test)
 subprocess.run(['cc','-std=c11','-Wno-format','-Werror=implicit-function-declaration',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
