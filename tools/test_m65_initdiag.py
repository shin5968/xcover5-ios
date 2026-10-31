"""Execute the actual M65 implementation with mocked IRQ/scheduler services."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT / 'xnu/patches/0091-xcover5-launchd-init-watch.patch').read_text()
source = ''.join(line[1:] for line in patch.split('+++ b/bsd/kern/xcover5_initdiag.c\n')[1].splitlines(True)
                 if line.startswith('+'))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('tree', nargs='?', type=Path)
parser.add_argument('--source-only', action='store_true')
parser.add_argument('--kernels', type=Path)
args = parser.parse_args()
if args.tree and args.tree.is_dir():
    assert (args.tree / 'bsd/kern/xcover5_initdiag.c').read_text() == source
    sleh = (args.tree / 'osfmk/arm64/sleh.c').read_text()
    assert sleh.count('xcover5_initdiag_svc(state);') == 1
    assert sleh.count('xcover5_initdiag_irq(state);') == 1
    assert sleh.index('sleh_interrupt_handler_prologue(state, DBG_INTR_TYPE_TIMER);') < sleh.index('xcover5_initdiag_irq(state);') < sleh.index('rtclock_intr(TRUE);')
    assert sleh.index('xcover5_initdiag_svc(state);') < sleh.index('if (trap_no == (int)PLATFORM_SYSCALL_TRAP_NO)')
    assert (args.tree / 'bsd/kern/bsd_init.c').read_text().count('xcover5_initdiag_init();') == 1
    assert (args.tree / 'bsd/conf/files').read_text().count('bsd/kern/xcover5_initdiag.c') == 1
elif args.tree:
    assert args.kernels, 'applied source missing without source-keyed kernel cache'
if args.kernels:
    kernels = [p for p in args.kernels.glob('kernel.*') if p.is_file()]
    assert kernels and all(b'XCOVER5 M65 INIT_DIAG' in p.read_bytes() and
                           b'M65 USER_IRQ' in p.read_bytes() and b'M65 STATE' in p.read_bytes()
                           for p in kernels)
if args.source_only:
    print('M65 applied implementation/SVC/timer IRQ/initialization hooks PASS before compilation')
    raise SystemExit(0)
body = source[source.index('#define XC_INIT_TICKS'):source.rindex('#endif')]
irq_body = body[body.index('void xcover5_initdiag_irq(arm_saved_state_t *regs)'):]
for forbidden in ('printf(', 'thread_reference(', 'thread_deallocate', 'proc_get', 'thread_call_'):
    assert forbidden not in irq_body, 'unsafe IRQ operation: ' + forbidden
for forbidden in ('copyin(', 'copyout(', 'thread_suspend(', 'thread_set_state(', 'get_user_regs('):
    assert forbidden not in body
prefix = r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <assert.h>
typedef int boolean_t;
#define FALSE 0
#define TRUE 1
static int interrupts=1,spin,threadlocked,in_irq,allocation_fail;
static unsigned scheduled,printed,last_tick;
struct Proc {int pid,ppid;unsigned uid;const char *p_comm;};
typedef struct Proc *proc_t;
struct Thread {uint64_t tid,wait_event;int state,wait_result,refs;void(*continuation)(void);struct Proc*p;};
typedef struct Thread *thread_t;
static struct Proc pid1={1,0,0,"launchd"},observer={6,1,0,"m39-probe"};
static struct Thread first={.tid=165,.refs=1,.p=&pid1},native={.tid=171,.refs=1,.p=&pid1},probe={.tid=180,.refs=1,.p=&observer};
static thread_t actor=&first;
static thread_t current_thread(void){return actor;}
static void *get_bsdthreadtask_info(thread_t t){assert(!in_irq);return t->p;}
static unsigned proc_getuid(proc_t p){assert(!in_irq);return p->uid;}
static int proc_getpid(proc_t p){assert(!in_irq);return p->pid;}
static int proc_ppid(proc_t p){assert(!in_irq);return p->ppid;}
static uint64_t thread_tid(thread_t t){assert(t&&t->refs>0);return t->tid;}
static void thread_reference(thread_t t){assert(!in_irq&&t->refs>0);t->refs++;}
static void thread_deallocate_safe(thread_t t){assert(!in_irq&&!spin&&!threadlocked&&interrupts&&t->refs>1);t->refs--;}
static boolean_t ml_set_interrupts_enabled(boolean_t enable){int old=interrupts;interrupts=enable;return old;}
#define LCK_GRP_DECLARE(name,label) int name __attribute__((unused))
#define LCK_SPIN_DECLARE(name,group) int name
static void lck_spin_lock(int*p){(void)p;assert(!interrupts&&!spin&&!threadlocked);spin=1;}
static void lck_spin_unlock(int*p){(void)p;assert(!interrupts&&spin);spin=0;}
static void thread_lock(thread_t t){assert(t&&!interrupts&&!spin&&!threadlocked);threadlocked=1;}
static void thread_unlock(thread_t t){assert(t&&!interrupts&&threadlocked);threadlocked=0;}
#define TH_RUN 4
#define TH_WAIT 1
#define TH_SUSP 2
#define TH_TERMINATE 16
typedef struct {int bits,trap;uint32_t cpsr;uint64_t pc,lr,sp,args[6];} arm_saved_state_t;
static int is_saved_state64(const arm_saved_state_t*s){return s->bits==64;}
static int get_saved_state_svc_number(const arm_saved_state_t*s){return s->trap;}
static uint32_t get_saved_state_cpsr(const arm_saved_state_t*s){return s->cpsr;}
#define PSR64_IS_USER64(cpsr) ((cpsr)==0)
static uint64_t get_saved_state_pc(const arm_saved_state_t*s){return s->pc;}
static uint64_t get_saved_state_lr(const arm_saved_state_t*s){return s->lr;}
static uint64_t get_saved_state_sp(const arm_saved_state_t*s){return s->sp;}
static uint64_t get_saved_state_reg(const arm_saved_state_t*s,unsigned n){assert(n<6);return s->args[n];}
static uint64_t mach_absolute_time(void){return 123456;}
typedef void *thread_call_param_t;typedef void *thread_call_t;
#define THREAD_CALL_PRIORITY_KERNEL 1
#define NSEC_PER_SEC 1000000000U
static thread_call_t thread_call_allocate_with_priority(void(*f)(void*,void*),void*p,int priority){assert(f&&!p&&priority==1);return allocation_fail?NULL:(void*)1;}
static void clock_interval_to_deadline(unsigned n,unsigned scale,uint64_t*out){assert(n==5&&scale==NSEC_PER_SEC);*out=500;}
static int thread_call_enter_delayed(thread_call_t c,uint64_t d){assert(c&&d==500&&!spin&&!threadlocked&&interrupts);scheduled++;return 0;}
static int diag_printf(const char*fmt,...){assert(!in_irq&&!spin&&!threadlocked&&interrupts);printed++;if(strstr(fmt,"M65 INIT tick=")){va_list args;va_start(args,fmt);last_tick=va_arg(args,unsigned);va_end(args);}return 0;}
#define printf diag_printf
'''
test = r'''
int main(void){
 arm_saved_state_t regs={.bits=64,.trap=73,.pc=0x1f932c2a4,.lr=0x1f92db0f8,.sp=0x160000000,.args={1,2,3,4,5,6}},before=regs;
 actor=NULL;interrupts=0;in_irq=1;xcover5_initdiag_irq(&regs);assert(!spin&&!interrupts);actor=&first;interrupts=1;in_irq=0;
 xcover5_initdiag_init();assert(xc_init_call&&printed==1&&!scheduled);
 xcover5_initdiag_svc(NULL);regs.bits=32;xcover5_initdiag_svc(&regs);regs.bits=64;
 pid1.uid=501;xcover5_initdiag_svc(&regs);pid1.uid=0;pid1.p_comm="other";xcover5_initdiag_svc(&regs);pid1.p_comm="launchd";
 assert(!xc_init.svc&&first.refs==1&&!scheduled);
 xcover5_initdiag_svc(&regs);assert(xc_init.target==&first&&first.refs==2&&scheduled==1&&xc_init.generation==1);
 xcover5_initdiag_svc(&regs);assert(first.refs==2&&scheduled==1&&xc_init.svc==2);
 actor=&native;xcover5_initdiag_svc(&regs);assert(first.refs==1&&native.refs==2&&xc_init.generation==2);
 native.state=TH_WAIT|TH_SUSP;native.wait_event=0x1234;native.wait_result=9;
 interrupts=0;in_irq=1;xcover5_initdiag_irq(&regs);assert(!interrupts&&xc_init.user.count==1&&xc_init.user.tid==171&&xc_init.user.pc==regs.pc&&xc_init.user.args[3]==4);
 regs.cpsr=4;regs.pc=0xfffffe0007001000;xcover5_initdiag_irq(&regs);assert(xc_init.kernel.count==1&&xc_init.kernel.pc==regs.pc);
 actor=&first;xcover5_initdiag_irq(&regs);assert(xc_init.kernel.count==1);actor=&native;
 in_irq=0;interrupts=1;regs=before;
 for(unsigned i=1;i<=12;i++){xc_init_tick(NULL,NULL);assert(last_tick==i);}
 assert(xc_init.done==2&&!xc_init.target&&native.refs==1&&scheduled==12);
 unsigned old=scheduled;uint64_t svc=xc_init.svc;xcover5_initdiag_svc(&regs);assert(scheduled==old&&xc_init.svc==svc&&native.refs==1);
 assert(!memcmp(&regs,&before,sizeof regs));
 memset(&xc_init,0,sizeof xc_init);scheduled=0;xcover5_initdiag_init();actor=&native;xcover5_initdiag_svc(&regs);assert(native.refs==2);
 actor=&probe;observer.ppid=2;xcover5_initdiag_svc(&regs);assert(!xc_init.done);observer.ppid=1;xcover5_initdiag_svc(&regs);assert(xc_init.done==1&&!xc_init.target&&native.refs==1);old=scheduled;xc_init_tick(NULL,NULL);assert(scheduled==old);
 memset(&xc_init,0,sizeof xc_init);scheduled=0;allocation_fail=1;actor=&native;xcover5_initdiag_init();xcover5_initdiag_svc(&regs);assert(!scheduled&&!xc_init.target&&native.refs==1);
 assert(!memcmp(&regs,&before,sizeof regs)&&first.refs==1&&native.refs==1&&probe.refs==1);
 puts("M65 actual body: IRQ masking/no unsafe IRQ calls, target replacement/ref balance, user/kernel PC distinction, scheduler locking, unchanged registers, observer stop,12-tick bound and allocation failure PASS");
}
'''
with tempfile.TemporaryDirectory() as temporary:
    d = Path(temporary);c = d / 'diag.c';c.write_text(prefix + body + test)
    subprocess.run(['cc', '-std=c11', '-O1', '-Wall', '-Wextra', '-Werror',
                    '-Wno-misleading-indentation', '-fsanitize=undefined', str(c), '-o', str(d / 'diag')], check=True)
    subprocess.run([str(d / 'diag')], check=True)
