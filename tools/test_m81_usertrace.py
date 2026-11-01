"""Exercise the actual pinned HackiOS user exception/abort trace with owned mocks."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
vendor=r/'third_party/hackios-diagnostics'
origin=json.loads((vendor/'ORIGIN.json').read_text())
for item in origin['files']:
    data=(vendor/item['path']).read_bytes()
    assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
upstream=(vendor/'user_exception_trace.c').read_text()
patch=(r/'xnu/patches/0096-xcover5-hackios-user-exception-trace.patch').read_text()
section=patch.split('+++ b/osfmk/arm64/user_exception_trace.c\n')[1].split('diff --git ')[0]
body=''.join(line[1:] for line in section.splitlines(True) if line.startswith('+'))
# The only differences from upstream, each applied exactly once.
ADAPT=[
 (' * addresses found by walking the frame pointers.\n */\n',
  ' * addresses found by walking the frame pointers.\n *\n * XCover5: from HackiOS a3384e031eb1e605cf37adaefc19991f04f6274b. There is no\n * Redwood loader log here, so every line goes to the console only; userabort\n * lines also need systrace, so a kernel without these boot-args prints nothing new.\n */\n'),
 ('\tif (task == kernel_task || state == NULL || !is_saved_state64(state)) {\n\t\treturn;\n\t}\n\tregion = vm_shared_region_get(task);\n\tif (region != NULL) {\n\t\tslide = region->sr_slide;\n\t\tvm_shared_region_deallocate(region);\n\t}\n\tprintf("userabort:',
  '\tif (!user_exception_trace_enabled || task == kernel_task || state == NULL || !is_saved_state64(state)) {\n\t\treturn;\n\t}\n\tregion = vm_shared_region_get(task);\n\tif (region != NULL) {\n\t\tslide = region->sr_slide;\n\t\tvm_shared_region_deallocate(region);\n\t}\n\tprintf("userabort:'),
 ("caught, or an assertion; the text of it goes to the program's standard error (boot-arg applog=1\n * puts that on the console), the stack is here.",
  "caught, or an assertion; the text of it goes to the program's standard error (the launchd jobs\n * that route it to /dev/console show it), the stack is here."),
 (" * the lines are few enough then to go to the loader's log as well, where all of a long run is kept.\n * ustacks_tname=* takes every thread, named or not, and sends them to the loader's log too.\n",
  ' * ustacks_tname=* takes every thread, named or not.\n'),
 ('extern void loader_log_line(const char *line);\n',''),
 ('\tprintf("%s", line);\n\tif (ustacks_tname[0] != 0) {\n\t\tloader_log_line(line);\n\t}\n','\tprintf("%s", line);\n'),
 ('(a debugging key sequence, see drivers/input/hakios.virtio_input.c)','(no caller on XCover5 yet; kept for a later input key sequence)'),
]
expected=upstream
for old,new in ADAPT:
    assert expected.count(old)==1,old[:50]
    expected=expected.replace(old,new)
assert body==expected and 'loader_log_line' not in body
assert body.count('static TUNABLE(uint32_t, user_exception_trace_enabled, "systrace", 0);')==1
hooks=patch.split('\ndiff --git ')[1:]
assert sum('+osfmk/arm64/user_exception_trace.c\tstandard' in h for h in hooks)==1
if len(sys.argv)>1:
    tree=Path(sys.argv[1])
    assert (tree/'osfmk/arm64/user_exception_trace.c').read_text()==body
    assert (tree/'osfmk/conf/files.arm64').read_text().count('osfmk/arm64/user_exception_trace.c\tstandard\n')==1
    e=(tree/'osfmk/kern/exception.c').read_text().split('\nexception_triage_thread(\n')[1].split('\n}\n')[0]
    assert e.count('user_exception_trace(exception, code, codeCnt, thread);')==1
    assert e.index('user_exception_trace(')<e.index('assert(exception != EXC_RPC_ALERT);')
    k=(tree/'bsd/kern/kern_sig.c').read_text().split('\n__pthread_kill(')[1].split('\n}\n')[0]
    assert k.count('user_abort_trace();')==1 and k.index('if (signum == SIGABRT)')<k.index('port_name_to_thread(')
    if '--source-only' in sys.argv:
        print('M81 actual applied user trace source, exception/abort hooks and build entry PASS');sys.exit(0)
traces=body.split('/*\n * Boot-args ustacks=')[0]
harness=r'''
#include <assert.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef int exception_type_t;typedef int64_t *mach_exception_data_t;typedef unsigned mach_msg_type_number_t;
typedef uint64_t user_addr_t;typedef size_t vm_size_t;
enum {EXC_BAD_ACCESS=1,EXC_BAD_INSTRUCTION=2,EXC_ARITHMETIC=3,EXC_SOFTWARE=5,EXC_BREAKPOINT=6};
#define MACH_VM_MAX_ADDRESS 0x0000000FC0000000ULL
#define TUNABLE(type,name,key,value) type name = value
struct proc {const char *name;int pid;};
typedef struct {uint64_t x[29],fp,lr,sp,pc;bool wide;} arm_saved_state_t;
struct task {struct proc *proc;};typedef struct task *task_t;
struct thread {task_t task;arm_saved_state_t *state;};typedef struct thread *thread_t;
struct vm_shared_region {uint32_t sr_slide;};typedef struct vm_shared_region *vm_shared_region_t;
static struct task kernel_task_s;
#define kernel_task (&kernel_task_s)
static struct thread *cur;static struct vm_shared_region region={0x1d3c000};static int region_refs;
static thread_t current_thread(void){return cur;}
static task_t get_threadtask(thread_t t){return t->task;}
static const arm_saved_state_t *get_user_regs(thread_t t){return t->state;}
static bool is_saved_state64(const arm_saved_state_t *s){return s->wide;}
static vm_shared_region_t vm_shared_region_get(task_t t){(void)t;region_refs++;return &region;}
static void vm_shared_region_deallocate(vm_shared_region_t r){assert(r==&region);region_refs--;}
static void *get_bsdtask_info(task_t t){return t->proc;}
char *proc_name_address(struct proc *p){return (char *)p->name;}
static int proc_pid(struct proc *p){return p->pid;}
static uint64_t get_saved_state_pc(const arm_saved_state_t *s){return s->pc;}
static uint64_t get_saved_state_lr(const arm_saved_state_t *s){return s->lr;}
static uint64_t get_saved_state_sp(const arm_saved_state_t *s){return s->sp;}
static uint64_t get_saved_state_fp(const arm_saved_state_t *s){return s->fp;}
static uint64_t get_saved_state_reg(const arm_saved_state_t *s,unsigned i){assert(i<29);return s->x[i];}
/* owned user memory: a handful of mapped ranges, everything else faults */
static struct {uint64_t at;unsigned char bytes[512];size_t size;} mem[40];static unsigned mapped;
static void map(uint64_t at,const void *data,size_t size){assert(mapped<40&&size<=512);mem[mapped].at=at;memcpy(mem[mapped].bytes,data,size);mem[mapped++].size=size;}
static const unsigned char *find(uint64_t at,size_t size){for(unsigned i=0;i<mapped;i++)if(at>=mem[i].at&&at+size<=mem[i].at+mem[i].size)return mem[i].bytes+(at-mem[i].at);return NULL;}
static int copyin(user_addr_t from,void *to,size_t size){const unsigned char *p=find(from,size);if(!p)return 14;memcpy(to,p,size);return 0;}
static int copyinstr(user_addr_t from,void *to,size_t max,vm_size_t *done){char *out=to;for(size_t i=0;i<max;i++){const unsigned char *p=find(from+i,1);if(!p){*done=i;return 14;}out[i]=*p;if(!*p){*done=i+1;return 0;}}*done=max;return 63;}
static void bzero(void *p,size_t n){memset(p,0,n);}
static char logs[16384];static size_t used;
static int capture(const char *fmt,...){va_list a;va_start(a,fmt);int n=vsnprintf(logs+used,sizeof(logs)-used,fmt,a);va_end(a);used+=n;assert(used<sizeof(logs));return n;}
#define printf capture
#include "traces.inc"
static unsigned count(const char *needle){unsigned n=0;for(const char *p=logs;(p=strstr(p,needle));p++)n++;return n;}
static void reset(void){used=0;logs[0]=0;mapped=0;}
static void frame(uint64_t fp,uint64_t next,uint64_t ret){uint64_t f[2]={next,ret};map(fp,f,sizeof(f));}
int main(void){
 struct proc sb={"SpringBoard",9},ld={"launchd",1};struct task t={&sb};
 arm_saved_state_t s={0};s.wide=true;s.pc=0x1a0001234;s.lr=0x1a0005678;s.sp=0x16fd00000;
 struct thread th={&t,&s},other={&t,&s};cur=&th;int64_t code[2]={1,0x41};
 static const char message[]="Failed to find the main CADisplay";static const unsigned char binary[]={1,2,3,4,5,6,7,0};
 user_exception_trace(EXC_BREAKPOINT,code,2,&th);user_abort_trace();assert(used==0);  /* default: silent */
 user_exception_trace_enabled=1;
 user_exception_trace(EXC_SOFTWARE,code,2,&th);user_exception_trace(EXC_BREAKPOINT,code,2,&other);
 struct task kt={&sb};kernel_task_s=kt;th.task=kernel_task;user_exception_trace(EXC_BAD_ACCESS,code,2,&th);th.task=&t;
 s.wide=false;user_exception_trace(EXC_BAD_ACCESS,code,2,&th);user_abort_trace();s.wide=true;assert(used==0);
 /* breakpoint: message register text, unmapped/short/binary/small values skipped, fp walk stops when not rising */
 map(0x105000000,message,sizeof(message));map(0x105001000,binary,sizeof(binary));map(0x105002000,"abc",4);
 s.x[0]=0x105000000;s.x[1]=0x1234;s.x[2]=0x105001000;s.x[3]=0x105002000;s.x[8]=0x109000000;s.x[16]=0x10000000000000ULL;
 s.fp=0x16fd00100;frame(0x16fd00100,0x16fd00200,0x1a0100000);frame(0x16fd00200,0x16fd00300,0x1a0200000);frame(0x16fd00300,0x16fd00200,0x1a0300000);
 user_exception_trace(EXC_BREAKPOINT,code,2,&th);
 assert(strstr(logs,"usertrap: SpringBoard[9] exception 6 code 0x1 0x41: pc 0x1a0001234 lr 0x1a0005678 sp 0x16fd00000, shared cache slide 0x1d3c000\n"));
 assert(strstr(logs,"usertrap:   x0 -> \"Failed to find the main CADisplay\"\n")&&count("usertrap:   x")==1);
 assert(count("called from")==3&&strstr(logs,"called from 0x1a0300000\n")&&region_refs==0);
 /* bounded: 10 return addresses; a misaligned fp yields none */
 reset();for(unsigned i=0;i<15;i++)frame(0x16fe00000+i*0x100,0x16fe00000+(i+1)*0x100,0x1b0000000+i);
 memset(s.x,0,sizeof(s.x));s.fp=0x16fe00000;user_exception_trace(EXC_BAD_ACCESS,code,1,&th);
 assert(count("called from")==10&&strstr(logs,"code 0x1 0x0:")&&strstr(logs,"called from 0x1b0000009\n")&&!strstr(logs,"0x1b000000a"));
 reset();s.fp=0x16fe00004;user_exception_trace(EXC_ARITHMETIC,code,0,&th);assert(count("usertrap:")==1&&count("called from")==0);
 /* abort: one line, at most 24 return addresses */
 reset();t.proc=&ld;for(unsigned i=0;i<30;i++)frame(0x16fe00000+i*0x100,0x16fe00000+(i+1)*0x100,0x1c0000000+i);
 s.fp=0x16fe00000;user_abort_trace();
 const char *want="userabort: launchd[1] aborts, shared cache slide 0x1d3c000; called from: 0x1c0000000 0x1c0000001 ";
 assert(!strncmp(logs,want,strlen(want)));
 assert(strstr(logs," 0x1c0000017\n")&&!strstr(logs,"0x1c0000018")&&count("\n")==1&&region_refs==0);
 puts("M81 actual usertrap/userabort: default silent, fatal-only filter, message text, slide, bounded frame walk PASS");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);(d/'traces.inc').write_text(''.join(l for l in traces.splitlines(True) if not l.startswith('#include')))
    (d/'test.c').write_text(harness)
    subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Wno-unused-function','-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all',str(d/'test.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
