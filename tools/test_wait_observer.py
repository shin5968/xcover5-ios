"""Compile actual patched observer with lifecycle/locking mocks, not a scheduler."""
from pathlib import Path
import subprocess, sys, tempfile
source = (Path(sys.argv[1])/'bsd/kern/sweet_exec_diag.c').read_text()
source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
head = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
#define ARM64_BOARD_CONFIG_SWEET 1
typedef int boolean_t, wait_result_t, kern_return_t, spl_t;
typedef void *event_t;
typedef void (*thread_continue_t)(void *,wait_result_t);
#define TRUE 1
#define FALSE 0
#define PROC_NULL NULL
#define TASK_NULL NULL
#define THREAD_NULL NULL
#define THREAD_UNINT 0
#define THREAD_CONTINUE_NULL NULL
#define NSEC_PER_SEC 1000000000
#define KERN_SUCCESS 0
#define MAXCOMLEN 16
struct thread { uint64_t thread_id,wait_event,last_run_time; thread_continue_t continuation;
 int state,block_hint,sched_pri,c_switch,syscalls_unix,syscalls_mach,refs; };
typedef struct thread *thread_t;
struct task { int thread_count,active,busy,refs; thread_t threads[12]; };
typedef struct task *task_t;
struct proc { int pid; char p_comm[17]; task_t task; int refs; };
typedef struct proc *proc_t;
static int spin, tasklocked, thlocked, proclocks, starts, stopped, delays, blocks, lastpid, samples, busy_lines, gone_lines;
static struct proc *procs[64];
static thread_continue_t callback;
static struct thread worker;
#define LCK_GRP_DECLARE(n,x) int n
#define LCK_SPIN_DECLARE(n,g) int n
static void lck_spin_lock(int *p){ (void)p; assert(!spin);spin=1; }
static void lck_spin_unlock(int *p){(void)p;assert(spin);spin=0;}
static int proc_getpid(proc_t p){return p->pid;}
static size_t strlcpy(char *d,const char*s,size_t n){size_t l=strlen(s);if(n){size_t k=l<n-1?l:n-1;memcpy(d,s,k);d[k]=0;}return l;}
static void proc_lock(proc_t p){(void)p;proclocks++;}
static void proc_unlock(proc_t p){(void)p;proclocks--;}
static proc_t proc_find(int pid){proc_t p=procs[pid];if(p)p->refs++;return p;}
static void proc_rele(proc_t p){assert(p->refs>0);p->refs--;}
static task_t proc_task(proc_t p){return p->task;}
static void task_reference(task_t t){t->refs++;}
static void task_deallocate(task_t t){assert(t->refs>0);t->refs--;}
static int task_lock_try(task_t t){assert(!tasklocked);if(t->busy)return 0;tasklocked=1;return 1;}
static void task_unlock(task_t t){(void)t;assert(tasklocked);tasklocked=0;}
#define queue_iterate(q,th,type,field) for(int qi=0;qi<task->thread_count && ((th)=task->threads[qi]);qi++)
static void thread_reference(thread_t t){assert(tasklocked);t->refs++;}
static void thread_deallocate(thread_t t){assert(!tasklocked&&!thlocked);assert(t->refs>0);t->refs--;}
static spl_t splsched(void){return 0;}
static void splx(spl_t s){(void)s;assert(!thlocked);}
static void thread_lock(thread_t t){(void)t;assert(!thlocked);thlocked=1;}
static void thread_unlock(thread_t t){(void)t;assert(thlocked);thlocked=0;}
static int logprintf(const char *fmt,...){assert(!spin&&!tasklocked&&!thlocked&&!proclocks);
 va_list a;va_start(a,fmt);
 if(strstr(fmt,"WAIT TH")){lastpid=va_arg(a,int);samples++;}
 if(strstr(fmt,"TASK_BUSY"))busy_lines++;
 if(strstr(fmt,"WAIT GONE"))gone_lines++;
 va_end(a);return 0;}
#define printf logprintf
static void assert_wait_timeout(event_t e,int i,int interval,int scale){(void)e;(void)i;assert(interval==20&&scale==NSEC_PER_SEC);delays++;}
static void thread_block(thread_continue_t c){assert(c==NULL);blocks++;}
static void thread_terminate_self(void){stopped++;}
static int kernel_thread_start(thread_continue_t c,void*a,thread_t*out){assert(!spin&&!tasklocked&&!thlocked);assert(a==NULL);callback=c;*out=&worker;worker.refs++;starts++;return 0;}
'''
tail = r'''
int main(void) {
 struct thread th[10]={0};struct task task={.thread_count=10,.active=1};
 for(int i=0;i<10;i++){task.threads[i]=&th[i];th[i].thread_id=i+1;th[i].state=1;th[i].block_hint=2;}
 struct proc init={1,"launchd",&task,0}, child={5,"xpcproxy",&task,0}, prior={3,"m34-probe",&task,0};
 procs[1]=&init;procs[5]=&child;procs[3]=&prior;
 sweet_exec_diag_record(&prior,1,0,0,0,"m34-probe");assert(starts==0);
 sweet_exec_diag_record(&child,1,0,0,0,"xpcproxy");assert(starts==0);
 sweet_exec_diag_record(&init,1,0,0,0,"launchd.ios");assert(starts==1&&worker.refs==0);
 sweet_exec_diag_record(&init,1,0,0,0,"launchd.ios");assert(starts==1);
 callback(NULL,0);assert(samples==64&&lastpid==5&&delays==4&&blocks==4&&stopped==1);
 assert(init.refs==0&&child.refs==0&&prior.refs==0&&task.refs==0);
 for(int i=0;i<10;i++)assert(th[i].refs==0);
 task.busy=1;sweet_wait_process(1);assert(busy_lines==1&&task.refs==0&&init.refs==0);
 procs[5]=NULL;sweet_wait_process(5);assert(gone_lines==1);
 task.busy=0;task.thread_count=0;sweet_wait_process(1);assert(task.refs==0);
 init.task=NULL;sweet_wait_process(1);assert(init.refs==0);
 puts("Actual observer mock checks PASS: one start, four bounded rounds, selected chain, eight-thread cap, balanced references, gone/no-task/busy/empty cases, no printing under locks. Kernel scheduling not simulated.");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 root = Path(tmp)
 c = root/'observer-test.c'
 c.write_text(head+source+tail)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-variable',str(c),'-o',str(root/'observer-test')],check=True)
 subprocess.run([str(root/'observer-test')],check=True)
