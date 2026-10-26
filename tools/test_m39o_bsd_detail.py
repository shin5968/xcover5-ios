"""Compile actual M39O header and verify bounded read-only failure evidence."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0066-xcover5-preferences-bsd-detail.patch').read_text()
h=''.join(x[1:] for x in p.split('+++ b/security/xcover5_prefs_bsd_detail.h\n',1)[1].splitlines(True) if x.startswith('+'))
p=(r/'xnu/patches/0067-xcover5-preferences-final-page.patch').read_text()
h=''.join(x[1:] for x in p.splitlines(True) if x.startswith('+') and not x.startswith('+++'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_bsd_detail.h').read_text()==h
 source=(t/'bsd/dev/arm/systemcalls.c').read_text()
 assert source.count('xcover5_prefs_bsd_detail(proc,code,error,&uthread->uu_arg[0]);')==1
 assert (t/'bsd/kern/kern_exit.c').read_text().count('xcover5_prefs_bsd_detail_dump(p);')==1
 at=source.index('xcover5_prefs_bsd_detail(proc,code,error,&uthread->uu_arg[0]);');assert source.index('AUDIT_SYSCALL_EXIT(code, proc, uthread, error);',at)>at
prefix=r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#define user_addr_t uintptr_t
#define XC_PREFS_BSD_HOST 1
#define NSEC_PER_SEC 1000000000U
#define THREAD_CALL_PRIORITY_KERNEL 1
#define os_atomic_cmpxchg(p,o,n,m) __sync_bool_compare_and_swap(p,o,n)
#define os_atomic_inc_orig(p,o) __atomic_fetch_add((p),1,__ATOMIC_RELAXED)
#define os_atomic_store(p,v,o) __atomic_store_n((p),(v),__ATOMIC_RELEASE)
#define os_atomic_load(p,o) __atomic_load_n((p),__ATOMIC_ACQUIRE)
struct proc {int uid,bits;const char *p_comm;};typedef struct proc *proc_t;
typedef void *thread_call_param_t;
typedef void (*thread_call_func_t)(void*,void*);
struct mock_call {thread_call_func_t callback;void *arg;};typedef struct mock_call *thread_call_t;
static struct mock_call mock_call;static unsigned allocations,schedules,callbacks;static int fail_allocate;
static thread_call_t thread_call_allocate_with_priority(thread_call_func_t f,void *a,int priority){assert(priority==THREAD_CALL_PRIORITY_KERNEL);allocations++;if(fail_allocate)return NULL;mock_call.callback=f;mock_call.arg=a;return &mock_call;}
static void clock_interval_to_deadline(unsigned n,unsigned scale,uint64_t *d){assert(n==2&&scale==NSEC_PER_SEC);*d=2000000000ULL;}
static int thread_call_enter_delayed(thread_call_t c,uint64_t d){assert(c==&mock_call&&d==2000000000ULL);schedules++;return 0;}

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
 xcover5_prefs_bsd_detail(&actor,121,EIO,a);assert(loglength==0);xcover5_prefs_bsd_detail_dump(&actor);
 assert(strstr(logtext,"call=121 rc=5 fd=2")&&strstr(logtext,"M39D SOURCE_SYNC writeFailed=1")&&strstr(logtext,"copy=14"));
 assert(!memcmp(saved,a,sizeof(a))&&msg[sizeof(msg)-2]=='\n');
 a[0]=(uint64_t)-2;a[1]=(uintptr_t)"/var/root/Library/Preferences/org.xcover5.m39.plist";a[3]=0x20;
 xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);xcover5_prefs_bsd_detail_dump(&actor);assert(strstr(logtext,"call=470 rc=2 fd=-2")&&strstr(logtext,"flags=20 copy=0")&&strstr(logtext,"org.xcover5.m39.plist"));
 unsigned count=xc_prefs_bsd_detail_total;
 actor.uid=501;xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.uid=0;
 actor.bits=0;xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.bits=1;
 actor.p_comm="other";xcover5_prefs_bsd_detail(&actor,121,EIO,a);actor.p_comm="m39-probe";
 xcover5_prefs_bsd_detail(&actor,120,EIO,a);xcover5_prefs_bsd_detail(&actor,121,0,a);assert(count==xc_prefs_bsd_detail_total);
 a[1]=1;xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);xcover5_prefs_bsd_detail_dump(&actor);assert(strstr(logtext,"copy=14 bytes=0"));
 a[2]=6;xcover5_prefs_bsd_detail(&actor,121,EIO,a);xcover5_prefs_bsd_detail_dump(&actor);assert(strstr(logtext,"count=6 shown=4")&&strstr(logtext,"descriptor_copy=14"));
 char big[201];memset(big,'x',200);big[200]=0;a[1]=(uintptr_t)big;xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);xcover5_prefs_bsd_detail_dump(&actor);char expected[64];snprintf(expected,sizeof(expected),"copy=%d bytes=160",ENAMETOOLONG);assert(strstr(logtext,expected));
 actor.p_comm="cfprefsd";
 for(unsigned i=0;i<20;i++)xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);
 actor.p_comm="m39-probe";xcover5_prefs_bsd_detail_dump(&actor);assert(strstr(logtext,"overflow=9 inflight=0"));
 assert(!strstr(logtext,"seq=16 pid="));
 xc_prefs_bsd_details[0].ready=0;xcover5_prefs_bsd_detail_dump(&actor);assert(strstr(logtext,"overflow=9 inflight=1"));
 assert(allocations==1&&schedules==1&&callbacks==0);
 actor.p_comm=NULL;actor.uid=501;memset(msg,'z',sizeof(msg)-1);
 callbacks++;mock_call.callback(mock_call.arg,NULL);
 assert(strstr(logtext,"M39P FINAL_DIAGNOSTICS")&&strstr(logtext,"M39D SOURCE_SYNC writeFailed=1")&&strstr(logtext,"M39P FINAL_END"));
 xc_prefs_bsd_detail_total=0;xc_prefs_detail_late_call=NULL;xc_prefs_detail_late_queued=0;memset(xc_prefs_bsd_details,0,sizeof(xc_prefs_bsd_details));
 fail_allocate=1;actor.uid=0;actor.p_comm="m39-probe";xcover5_prefs_bsd_detail(&actor,470,ENOENT,a);xcover5_prefs_bsd_detail_dump(&actor);
 assert(strstr(logtext,"NO_LATE_HANDLE")&&allocations==2&&schedules==1);
 puts("M39P delayed callback: queue once, static snapshot after proc expiry, no blocking sleep, allocation failure fallback PASS (host only)");
 puts("M39O actual header: lost-writev text, fd/path ABI, scope, copy faults, bounded truncation and unchanged inputs PASS (host only)");
}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+h+test)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
