# Actual boot monitor against mocked proc/register/timer services; no device proof.
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0085-xcover5-launchd-boot-watch.patch').read_text()
source=''.join(x[1:] for x in p.split('+++ b/bsd/kern/xcover5_bootdiag.c\n')[1].splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'bsd/kern/xcover5_bootdiag.c').read_text()==source
 s=(t/'osfmk/arm64/sleh.c').read_text()
 assert s.count('xcover5_bootdiag_svc(state,1);')==1 and s.count('xcover5_bootdiag_svc(state,2);')==2
 assert 'if(trap_no!=MACH_ARM_TRAP_ABSTIME && trap_no!=MACH_ARM_TRAP_CONTTIME)' in s
 assert s.index('xcover5_bootdiag_svc(state,1);')<s.index('if (trap_no == (int)PLATFORM_SYSCALL_TRAP_NO)')
 assert (t/'bsd/dev/arm/systemcalls.c').read_text().count('xcover5_bootdiag_svc(regs,2);')==1
 assert (t/'bsd/kern/bsd_init.c').read_text().count('xcover5_bootdiag_init();')==1
 assert (t/'bsd/conf/files').read_text().count('bsd/kern/xcover5_bootdiag.c')==1
 if '--source-only' in sys.argv:
  print('M50B actual applied source and all boot-hook placements PASS (before kernel compile)')
  raise SystemExit(0)
body=source[source.index('#define XC_BOOT_EVENTS'):source.rindex('#endif')]
prefix=r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <assert.h>
struct Proc{int pid,ppid;unsigned uid;const char*p_comm;};typedef struct Proc*proc_t;
static struct Proc actor={1,0,0,"launchd.ios"};static unsigned locks,scheduled,allocation_fail,printed,last_tick;
typedef void*thread_t;static thread_t current_thread(void){return(void*)1;}
static void*get_bsdthreadtask_info(thread_t t){assert(t);return &actor;}
static int proc_getpid(proc_t p){return p->pid;}static int proc_ppid(proc_t p){return p->ppid;}static unsigned proc_getuid(proc_t p){return p->uid;}
static uint64_t thread_tid(thread_t t){assert(t);return 77;}
typedef struct{unsigned bits;int trap;uint64_t pc,lr,sp,args[6];}arm_saved_state_t;
static int is_saved_state64(const arm_saved_state_t*s){return s->bits==64;}
static int get_saved_state_svc_number(const arm_saved_state_t*s){return s->trap;}
static uint64_t get_saved_state_pc(const arm_saved_state_t*s){return s->pc;}
static uint64_t get_saved_state_lr(const arm_saved_state_t*s){return s->lr;}
static uint64_t get_saved_state_sp(const arm_saved_state_t*s){return s->sp;}
static uint64_t get_saved_state_reg(const arm_saved_state_t*s,unsigned n){assert(n<6);return s->args[n];}
static uint64_t mach_absolute_time(void){return 12345;}
#define LCK_GRP_DECLARE(name,label) int name __attribute__((unused))
#define LCK_SPIN_DECLARE(name,group) int name
static void lck_spin_lock(int*p){(void)p;assert(!locks);locks=1;}
static void lck_spin_unlock(int*p){(void)p;assert(locks);locks=0;}
typedef void*thread_call_param_t;typedef void*thread_call_t;
#define THREAD_CALL_PRIORITY_KERNEL 1
#define NSEC_PER_SEC 1000000000U
static thread_call_t thread_call_allocate_with_priority(void(*f)(void*,void*),void*p,int priority){assert(f&&!p&&priority==1);return allocation_fail?NULL:(void*)1;}
static void clock_interval_to_deadline(unsigned n,unsigned scale,uint64_t*out){assert(n==5&&scale==NSEC_PER_SEC);*out=500;}
static int thread_call_enter_delayed(thread_call_t call,uint64_t deadline){assert(call&&deadline==500&&!locks);scheduled++;return 0;}
static int boot_printf(const char*fmt,...){assert(!locks);printed++;if(strstr(fmt,"BOOT_END")){va_list a;va_start(a,fmt);last_tick=va_arg(a,unsigned);va_end(a);}return 0;}
#define printf boot_printf
'''
test=r'''
int main(void){arm_saved_state_t regs={.bits=64,.trap=-47,.pc=0x180001000,.lr=0x180002000,.sp=0x160001000,.args={1,2,3,4,5,6}},before=regs;
xcover5_bootdiag_init();assert(xc_boot_call&&printed==1&&!scheduled);
xcover5_bootdiag_svc(NULL,1);regs.bits=32;xcover5_bootdiag_svc(&regs,1);regs.bits=64;
xcover5_bootdiag_svc(&regs,3);actor.uid=501;xcover5_bootdiag_svc(&regs,1);actor.uid=0;
actor.p_comm="other";xcover5_bootdiag_svc(&regs,1);actor.p_comm="launchd.ios";assert(!xc_boot.total&&!scheduled);
xcover5_bootdiag_svc(&regs,1);assert(xc_boot.total==1&&xc_boot.count==1&&scheduled==1&&xc_boot.events[0].phase==1);
assert(xc_boot.events[0].trap==-47&&xc_boot.events[0].tid==77&&xc_boot.events[0].pc==regs.pc&&xc_boot.events[0].args[5]==6);
regs.args[0]=0;xcover5_bootdiag_svc(&regs,2);regs.args[0]=1;assert(xc_boot.events[1].phase==2&&xc_boot.events[1].args[0]==0);
for(unsigned i=0;i<20;i++)xcover5_bootdiag_svc(&regs,1);assert(xc_boot.count==8&&xc_boot.total==22&&scheduled==1);
for(unsigned i=0;i<8;i++)assert(xc_boot.events[(xc_boot.next+i)%8].seq==15+i);
xc_boot_tick(NULL,NULL);assert(last_tick==1&&scheduled==2&&xc_boot.ticks==1);
xc_boot_tick(NULL,NULL);xc_boot_tick(NULL,NULL);assert(last_tick==3&&scheduled==3&&xc_boot.ticks==3);
unsigned kept=printed;xc_boot_tick(NULL,NULL);assert(printed==kept&&scheduled==3);
assert(!memcmp(&regs,&before,sizeof regs));
actor.pid=6;actor.ppid=2;actor.p_comm="m39-probe";xcover5_bootdiag_svc(&regs,1);assert(!xc_boot.probe);
actor.ppid=1;xcover5_bootdiag_svc(&regs,1);assert(xc_boot.probe);kept=printed;xc_boot_tick(NULL,NULL);assert(printed==kept);
actor.pid=1;actor.p_comm="launchd.ios";xcover5_bootdiag_svc(&regs,1);assert(xc_boot.total==22);
memset(&xc_boot,0,sizeof xc_boot);actor=(struct Proc){1,0,0,"launchd"};scheduled=0;allocation_fail=1;
xcover5_bootdiag_init();assert(!xc_boot_call);xcover5_bootdiag_svc(&regs,1);assert(xc_boot.total==1&&!scheduled);
memset(&xc_boot,0,sizeof xc_boot);allocation_fail=0;xcover5_bootdiag_init();xcover5_bootdiag_svc(&regs,1);
actor=(struct Proc){6,1,0,"m39-probe"};xcover5_bootdiag_svc(&regs,1);kept=printed;xc_boot_tick(NULL,NULL);assert(printed==kept&&scheduled==1);
puts("M50B actual monitor: root/PID/name filters, raw BSD/Mach register capture, untouched registers, bounded ordered ring, three ticks, probe suppression and allocation failure PASS; hooks verified when applied tree supplied");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);f=d/'monitor.c';f.write_text(prefix+body+test)
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined',str(f),'-o',str(d/'monitor')],check=True)
 subprocess.run([str(d/'monitor')],check=True)
