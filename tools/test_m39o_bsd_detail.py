"""Compile actual M39O header and verify bounded read-only failure evidence."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0066-xcover5-preferences-bsd-detail.patch').read_text()
h=''.join(x[1:] for x in p.split('+++ b/security/xcover5_prefs_bsd_detail.h\n',1)[1].splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_bsd_detail.h').read_text()==h
 source=(t/'bsd/dev/arm/systemcalls.c').read_text()
 assert source.count('xcover5_prefs_bsd_detail(proc,code,error,&uthread->uu_arg[0]);')==1
 at=source.index('xcover5_prefs_bsd_detail(proc,code,error,&uthread->uu_arg[0]);');assert source.index('AUDIT_SYSCALL_EXIT(code, proc, uthread, error);',at)>at
prefix=r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#define user_addr_t uintptr_t
#define os_atomic_inc_orig(p,o) __atomic_fetch_add((p),1,__ATOMIC_RELAXED)
struct proc {int uid,bits;const char *p_comm;};typedef struct proc *proc_t;
static unsigned proc_getuid(proc_t p){return p->uid;}
static int proc_is64bit_data(proc_t p){return p->bits;}
static int proc_pid(proc_t p){(void)p;return 6;}
static char logtext[32768];static size_t loglength;
static int detail_printf(const char *fmt,...){va_list a;va_start(a,fmt);int n=vsnprintf(logtext+loglength,sizeof(logtext)-loglength,fmt,a);va_end(a);assert(n>=0&&(size_t)n<sizeof(logtext)-loglength);loglength+=n;return n;}
#define printf detail_printf
static int copyin(user_addr_t a,void *b,size_t n){if(a<4096)return EFAULT;memcpy(b,(void*)a,n);return 0;}
static int copyinstr(user_addr_t a,char *b,size_t n,size_t *copied){if(a<4096)return EFAULT;size_t z=strlen((void*)a)+1;*copied=z<n?z:n;memcpy(b,(void*)a,*copied);return z>n?ENAMETOOLONG:0;}
"""
test=r"""
int main(void){
 struct proc actor={0,1,"m39-probe"};char msg[]="M39D SOURCE_SYNC writeFailed=1 volatile=0 readonly=0 directMode=0 result=0\n";
 struct {uint64_t base,length;} iov[2]={{(uintptr_t)msg,sizeof(msg)-1},{1,3}};
 uint64_t a[4]={2,(uintptr_t)iov,2,0},saved[4];memcpy(saved,a,sizeof(a));
 xcover5_prefs_bsd_detail(&actor,121,EIO,a);
 assert(strstr(logtext,"call=121 rc=5 fd=2")&&strstr(logtext,"M39D SOURCE_SYNC writeFailed=1")&&strstr(logtext,"copy=14"));
 assert(!memcmp(saved,a,sizeof(a))&&msg[sizeof(msg)-2]=='\n');
 a[0]=(uint64_t)-2;a[1]=(uintptr_t)"/var/root/Library/Preferences/org.xcover5.m39.plist";a[3]=0x20;
 xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);assert(strstr(logtext,"call=470 rc=2 fd=-2")&&strstr(logtext,"flags=20 copy=0")&&strstr(logtext,"org.xcover5.m39.plist"));
 unsigned count=xc_prefs_bsd_detail_total;
 actor.uid=501;xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.uid=0;
 actor.bits=0;xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.bits=1;
 actor.p_comm="other";xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.p_comm="m39-probe";
 xcover5_prefs_bsd_detail(&actor,120,EIO,a);xcover5_prefs_bsd_detail(&actor,121,0,a);assert(count==xc_prefs_bsd_detail_total);
 a[1]=1;xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);assert(strstr(logtext,"copy=14 bytes=0"));
 a[2]=6;xcover5_prefs_bsd_detail(&actor,121,EIO,a);assert(strstr(logtext,"count=6 shown=4")&&strstr(logtext,"descriptor_copy=14"));
 char big[201];memset(big,'x',200);big[200]=0;a[1]=(uintptr_t)big;xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);char expected[64];snprintf(expected,sizeof(expected),"copy=%d bytes=160",ENAMETOOLONG);assert(strstr(logtext,expected));
 actor.p_comm="cfprefsd";
 for(unsigned i=0;i<20;i++)xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);
 char *marker=strstr(logtext,"truncated cap=16");assert(marker&&!strstr(marker+1,"truncated cap=16"));
 assert(!strstr(logtext,"seq=16 pid="));
 puts("M39O actual header: lost-writev text, fd/path ABI, scope, copy faults, bounded truncation and unchanged inputs PASS (host only)");
}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+h+test)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
