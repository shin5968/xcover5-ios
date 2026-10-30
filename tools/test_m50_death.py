# Actual clientDied/registration/snapshot code, plus real POSIX pipe/SIGKILL tests.
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
scope={'__file__':str(r/'tools/test_m49_persistent.py')}
exec(compile((r/'tools/test_m49_persistent.py').read_text().split('with tempfile.TemporaryDirectory()')[0],'m49-harness-builder','exec'),scope)
patch=(r/'xnu/patches/0083-xcover5-panel-client-death.patch').read_text()
part=patch.split('+++ b/iokit/Kernel/arm/MiniIOSurface.cpp\n')[1].split('--- ')[0]
a=''.join(x[1:] for x in part.splitlines(True) if x.startswith('+'))
role=a[:a.index(' /* M50:')]
method=a[a.index(' IOReturn clientDied('):a.index('  if(selector==94)')]
register=a[a.index('  if(selector==94)'):]
auto=(r/'xnu/patches/0062-xcover5-usb-autolog.patch').read_text().split('+++ b/bsd/dev/xcover5_autolog.c\n')[1].split('--- ')[0]
auto=''.join(x[1:] for x in auto.splitlines(True) if x.startswith('+'))
auto=auto[auto.index('void xcover5_test_finish(proc_t p,int rv) {'):auto.index('static uint32_t usb_rd')]
guard=''.join(x[1:] for x in patch.split('+++ b/bsd/dev/xcover5_autolog.c\n')[1].splitlines(True) if x.startswith('+') and not x.startswith('+++'))
guard=guard[guard.index('    if(rv==9'):]
auto=auto.replace('    printf("XCOVER5 AUTO TEST_END',guard+'    printf("XCOVER5 AUTO TEST_END')
if len(sys.argv)>1:
 t=Path(sys.argv[1]);s=(t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert role in s and method in s and register in s
 assert auto in (t/'bsd/dev/xcover5_autolog.c').read_text()
kp=scope['kp'].replace('struct IOUserClient{static void free(){}};',r'''
struct IOUserClient{unsigned closed=0,base_calls=0;virtual int clientClose(){return 99;}
 int clientDied(){base_calls++;if(closed)return 99;closed=1;return clientClose();}static void free(){}};
struct Proc{unsigned uid=0,ppid=1,pid=19;uint64_t unique=101;const char*p_comm="m39-probe";};using proc_t=Proc*;static Proc actor;
static proc_t current_proc_EXTERNAL(){return &actor;}static unsigned proc_getuid(proc_t p){return p->uid;}
static unsigned proc_ppid(proc_t p){return p->ppid;}static unsigned proc_pid(proc_t p){return p->pid;}
static unsigned proc_getpid(proc_t p){return p->pid;}static uint64_t proc_uniqueid(proc_t p){return p->unique;}
static void proc_name(unsigned,char*n,size_t s){snprintf(n,s,"%s",actor.p_comm);}
#define bzero(p,n) memset(p,0,n)
#define kIOReturnNotPrivileged 7
static struct{unsigned size,crc,dropped;}xc_meta;static unsigned finishes,last_status;
static unsigned mach_absolute_time(){return 0;}static void xc_finish(unsigned,unsigned s){finishes++;last_status=s;}
''')
kt=r'''
return 5;}};
int main(){surface.kpixels=(uint8_t*)calloc(1,4262400);assert(surface.kpixels);Client c;Args a;
actor.uid=1;assert(c.call(94,&a)==7);actor.uid=0;actor.ppid=6;assert(c.call(94,&a)==7);actor.ppid=1;
actor.p_comm="other";assert(c.call(94,&a)==7);actor.p_comm="m39-probe";
a.scalarInputCount=1;assert(c.call(94,&a)==2);a.scalarInputCount=0;a.structureOutputDescriptor=(void*)1;assert(c.call(94,&a)==2);a.structureOutputDescriptor=nullptr;
assert(!c.call(94,&a)&&xcover5_expected_panel_death(&actor));assert(c.call(94,&a)==2);
actor.unique++;assert(!xcover5_expected_panel_death(&actor));actor.unique--;actor.pid++;assert(!xcover5_expected_panel_death(&actor));actor.pid--;
assert(!xcPersistentSubmit(&c.fPersistent,19,1,3)&&allocs==1);
assert(!c.clientDied()&&c.base_calls==1&&!allocs&&gPersistentStats[0]==1&&gPersistentStats[4]==4&&gPersistentStats[2]==19&&gPersistentStats[3]==1&&gPersistentStats[6]==3);
assert(c.clientDied()==99&&gPersistentStats[0]==1);c.free();assert(gPersistentStats[0]==1&&!allocs);
Client bad;assert(!xcPersistentSubmit(&bad.fPersistent,19,1,3));end_rc=1;assert(bad.clientDied()==4&&!allocs&&gPersistentStats[5]==1);end_rc=0;bad.free();
xcover5_test_finish(&actor,9);assert(!finishes);xcover5_test_finish(&actor,87<<8);assert(finishes==1&&last_status==(87<<8));
actor.unique++;xcover5_test_finish(&actor,9);assert(finishes==2);actor.unique--;actor.pid=6;
xcover5_test_finish(&actor,72<<8);assert(finishes==3&&last_status==(72<<8));actor.uid=501;xcover5_test_finish(&actor,9);assert(finishes==3);
free(surface.kpixels);puts("M50 actual clientDied: reason4/restore/free once, base guard, restore failure; root registration, unique-ID matching and only expected SIGKILL skips final capture PASS");}
'''
ipc=r'''
#include <assert.h>
#include <signal.h>
#include <sys/wait.h>
#include <stdio.h>
#include "panel-death-protocol.h"
int main(void){int p[2];assert(!pipe(p));struct m50_packet out={M50_STARTED,17,0,0},in={0};assert(!m50_send(p[1],&out));assert(!m50_receive(p[0],&in,20)&&in.pid==17);
assert(m50_receive(p[0],&in,5)==-1&&errno==ETIMEDOUT);close(p[1]);assert(m50_receive(p[0],&in,20)==-1&&errno==EPROTO);close(p[0]);
assert(!pipe(p));pid_t child=fork();assert(child>=0);if(!child){close(p[0]);struct m50_packet held={M50_HELD,(uint32_t)getpid(),7,3};
assert(write(p[1],&held,3)==3);assert(write(p[1],(char*)&held+3,sizeof(held)-3)==(ssize_t)sizeof(held)-3);for(;;)pause();}
close(p[1]);assert(!m50_receive(p[0],&in,1000)&&in.type==M50_HELD&&in.pid==(uint32_t)child&&in.sid==7);
assert(!kill(child,SIGKILL));int status;assert(waitpid(child,&status,0)==child&&WIFSIGNALED(status)&&WTERMSIG(status)==SIGKILL);char b;assert(read(p[0],&b,1)==0);close(p[0]);
uint64_t before[7]={4,0},after[7]={5,0,17,1,4,0,3};assert(m50_restore_valid(before,after,17));
for(unsigned i=0;i<7;i++){after[i]++;assert(!m50_restore_valid(before,after,17));after[i]--;}
assert(!m50_restore_valid(before,after,18));before[1]=1;assert(!m50_restore_valid(before,after,17));
puts("M50 actual IPC: fragmented records, timeout/EOF rejection, real SIGKILL/pipe EOF and all restore-proof fields PASS; no ported-kernel/device claim");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)
 wrapper='class Client:public IOUserClient{public:void*fLock=(void*)2;uint32_t fOwner=19;XCPersistentPanel fPersistent={};bool isInactive(){return false;}void terminate(){}\n'+method+scope['close']+'int call(unsigned selector,Args*a){\n'
 for name,text,compiler in [('death',kp+scope['abi']+scope['helper']+role+auto+wrapper+register+kt,'c++'),('ipc',ipc,'cc')]:
  f=d/(name+('.cpp' if compiler=='c++' else '.c'));f.write_text(text)
  subprocess.run([compiler,'-std=c++17' if compiler=='c++' else '-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-Wno-multichar','-fsanitize=undefined','-I'+str(r/'tools'),str(f),'-o',str(d/name)],check=True)
  subprocess.run([str(d/name)],check=True,timeout=10)
