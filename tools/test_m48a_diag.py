"""Validate actual diagnostic selector, bounds and retained snapshot under UBSan."""
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0081-xcover5-m40-readiness-diagnostic.patch').read_text()
added=''.join(line[1:] for line in p.splitlines(True) if line.startswith('+') and not line.startswith('+++'))
helper=added[added.index('static uint64_t gM40Diag'):added.index('static void xcM40DiagReport')]
handler=added[added.index('  if(selector==92)'):]
assert handler.endswith('  }\n')
if len(sys.argv)>1:
 applied=(Path(sys.argv[1])/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert helper in applied and handler in applied
prefix=r"""
#include <stdint.h>
#include <cstring>
#include <cassert>
#include <cstdio>
struct Proc{unsigned uid=0,ppid=1,pid=6;};static Proc process;using proc_t=Proc*;
static proc_t current_proc_EXTERNAL(){return &process;}
static unsigned proc_getuid(proc_t p){return p->uid;}static unsigned proc_ppid(proc_t p){return p->ppid;}
static unsigned proc_pid(proc_t p){return p->pid;}
static const char *actor="m39-probe";
static void proc_name(unsigned,char *n,unsigned size){snprintf(n,size,"%s",actor);}
#define bzero(p,n) memset(p,0,n)
static int gSurfaceLock;static unsigned reports;
static void IOLockLock(int){ }static void IOLockUnlock(int){ }
static void xcM40DiagReport(){reports++;}
const int kIOReturnSuccess=0,kIOReturnNotPrivileged=1,kIOReturnBadArgument=2;
struct Args{uint64_t *scalarInput=nullptr;unsigned scalarInputCount=0,scalarOutputCount=0;
 unsigned structureInputSize=0,structureOutputSize=0;void *structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;};
"""
test=r"""
 return 3;}
int main(){uint64_t v[12]={19,5,'R',0,0,0,2,0,0,1,0,0};Args a;a.scalarInput=v;a.scalarInputCount=12;
assert(!call(92,&a)&&reports==1&&gM40Diag[0]==6&&gM40Diag[2]==5);
uint64_t kept[13];memcpy(kept,gM40Diag,sizeof kept);
assert(call(92,nullptr)==2);a.scalarInput=nullptr;assert(call(92,&a)==2);a.scalarInput=v;
for(unsigned count:{0u,11u,13u}){a.scalarInputCount=count;assert(call(92,&a)==2);}a.scalarInputCount=12;
for(unsigned i=0;i<12;i++){auto saved=v[i];v[i]=~uint64_t(0);assert(call(92,&a)==2);v[i]=saved;}
v[0]=0;assert(call(92,&a)==2);v[0]=19;v[1]=11;assert(call(92,&a)==2);v[1]=5;
v[2]='X';assert(call(92,&a)==2);v[2]='R';v[3]=2;assert(call(92,&a)==2);v[3]=0;
v[6]=3;assert(call(92,&a)==2);v[6]=2;v[9]=0;assert(call(92,&a)==2);v[9]=1;
process.uid=1;assert(call(92,&a)==1);process.uid=0;process.ppid=6;assert(call(92,&a)==1);process.ppid=1;
actor="other";assert(call(92,&a)==1);actor="m39-probe";
a.scalarOutputCount=1;assert(call(92,&a)==2);a.scalarOutputCount=0;
a.structureInputDescriptor=(void*)1;assert(call(92,&a)==2);a.structureInputDescriptor=nullptr;
a.structureOutputDescriptor=(void*)1;assert(call(92,&a)==2);a.structureOutputDescriptor=nullptr;
a.structureInputSize=1;assert(call(92,&a)==2);a.structureInputSize=0;
a.structureOutputSize=1;assert(call(92,&a)==2);a.structureOutputSize=0;
assert(!memcmp(kept,gM40Diag,sizeof kept)&&reports==1);
v[3]=0xffffffffULL;v[6]=0xffffffffULL;v[4]=4;v[7]=5;v[10]=7;
assert(!call(92,&a)&&reports==2&&gM40Diag[4]==0xffffffffULL);
puts("M48A actual retained readiness selector: scalar bounds, identity, malformed rejection, unchanged snapshot PASS");}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);f=d/'test.cpp';f.write_text(prefix+'\n#include <initializer_list>\n'+helper+'\nstatic int call(unsigned selector,Args *a){\n'+handler+test)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(f),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
