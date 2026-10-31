"""Exercise the actual bounded register-only UI breakpoint logger."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
body=(r/'tools/ui-breakpoint-evidence.h').read_text()
patch=(r/'xnu/patches/0093-xcover5-ui-breakpoint-evidence.patch').read_text()
section=patch.split('+++ b/osfmk/arm64/xcover5_ui_breakpoint_evidence.h\n')[1]
assert ''.join(line[1:] for line in section.splitlines(True) if line.startswith('+'))==body
if len(sys.argv)>1:
    tree=Path(sys.argv[1]);s=(tree/'osfmk/arm64/sleh.c').read_text()
    assert (tree/'osfmk/arm64/xcover5_ui_breakpoint_evidence.h').read_text()==body
    b=s.split('handle_breakpoint(arm_saved_state_t *state, uint32_t esr __unused)\n{')[1].split('handle_watchpoint(')[0]
    assert b.count('xcover5_ui_breakpoint_evidence(state, esr);')==1
    assert b.index('xcover5_ui_breakpoint_evidence(')<b.index('exception_triage(exception, codes, numcodes);')
    assert 'codes[1] = get_saved_state_pc(state);' in b and '__builtin_unreachable();' in b
    assert '#include <kern/task.h>' in s
    if '--source-only' in sys.argv:
        print('M69 actual applied header and retained terminal breakpoint triage PASS');sys.exit(0)
harness=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
#include <string>
#define task_t M69TaskHandle
static std::string logs;static const char *name;static int pid=33;
struct State {uint64_t pc,lr,sp,fp,x[29];uint32_t cpsr;bool wide;};
typedef State arm_saved_state_t;
struct Task {uint64_t mach_header_vm_address;uint32_t task_shared_region_slide;};
static Task task={0x104000000ULL,0x1234000};typedef Task *task_t;
static task_t current_task(){return &task;}
static int proc_selfpid(){return pid;}
static void proc_name(int,char *s,int n){snprintf(s,n,"%s",name);}
static int capture(const char *fmt,...){char b[512];va_list args;va_start(args,fmt);int n=vsnprintf(b,sizeof(b),fmt,args);va_end(args);logs+=b;return n;}
#define printf capture
#define os_atomic_inc_orig(p,o) ((*(p))++)
#define ISS_BRK_COMMENT(esr) ((esr)&0xffff)
static uint64_t get_saved_state_pc(State*s){return s->pc;}
static uint64_t get_saved_state_lr(State*s){return s->lr;}
static uint64_t get_saved_state_sp(State*s){return s->sp;}
static uint32_t get_saved_state_cpsr(State*s){return s->cpsr;}
static bool is_saved_state64(State*s){return s->wide;}
static State* saved_state64(State*s){return s;}
#include "xcover5_ui_breakpoint_evidence.h"
int main(){
 State state={};state.pc=0x190001234;state.lr=0x190005678;state.sp=0x16ff10000;state.fp=0x16ff10010;state.wide=true;
 for(unsigned i=0;i<29;i++)state.x[i]=0x100+i;
 State before=state;Task old=task;
 name="other";xcover5_ui_breakpoint_evidence(&state,0xf2000001);assert(logs.empty());
 for(const char *n:{"SpringBoard","backboardd"}){name=n;for(unsigned i=0;i<10;i++)xcover5_ui_breakpoint_evidence(&state,0xf2000001);}
 assert(memcmp(&state,&before,sizeof(state))==0&&memcmp(&task,&old,sizeof(task))==0);
 unsigned count=0;for(size_t at=0;(at=logs.find("XCOVER5 M69 BRK",at))!=std::string::npos;at++)count++;
 assert(count==8&&logs.find("name=other")==std::string::npos);
 assert(logs.find("PC=0000000190001234 LR=0000000190005678")!=std::string::npos);
 assert(logs.find("MAIN=0000000104000000 CACHE_SLIDE=01234000")!=std::string::npos);
 assert(logs.find("X28=000000000000011c")!=std::string::npos);
 puts("M69 actual register logger: exact UI names, per-process-name cap, raw PC/LR/main/cache slide, unchanged task/state PASS");
}
'''
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);(d/'xcover5_ui_breakpoint_evidence.h').write_text(body);(d/'test.cpp').write_text(harness)
    subprocess.run(['c++','-std=c++17','-O1','-Wall','-Wextra','-fsanitize=undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
