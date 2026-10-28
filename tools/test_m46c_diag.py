"""Validate actual diagnostic selector, bounds and retained snapshot under UBSan."""
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0078-xcover5-reader-phase-diagnostic.patch').read_text()
added=''.join(line[1:] for line in p.splitlines(True) if line.startswith('+') and not line.startswith('+++'))
helper=added[added.index('static uint64_t gReaderDiag'):added.index('static void xcReaderDiagReport')]
handler=added[added.index('  if(selector==91)'):]
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
static void xcReaderDiagReport(){reports++;}
const int kIOReturnSuccess=0,kIOReturnNotPrivileged=1,kIOReturnBadArgument=2;
struct Args{uint64_t *scalarInput=nullptr;unsigned scalarInputCount=0,scalarOutputCount=0;
 unsigned structureInputSize=0,structureOutputSize=0;void *structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;};
"""
test=r"""
 return 3;}
int main(){uint64_t v[7]={19,1,0,1,5,9,1};Args a;a.scalarInput=v;a.scalarInputCount=7;
assert(!call(91,&a)&&reports==1&&gReaderDiag[0]==6&&gReaderDiag[5]==5);
uint64_t kept[8];memcpy(kept,gReaderDiag,sizeof kept);
assert(call(91,nullptr)==2);a.scalarInput=nullptr;assert(call(91,&a)==2);a.scalarInput=v;
for(unsigned count:{0u,6u,8u}){a.scalarInputCount=count;assert(call(91,&a)==2);}a.scalarInputCount=7;
for(unsigned i=0;i<7;i++){auto saved=v[i];v[i]=~uint64_t(0);assert(call(91,&a)==2);v[i]=saved;}
v[0]=0;assert(call(91,&a)==2);v[0]=19;v[1]=256;assert(call(91,&a)==2);v[1]=1;
v[2]=2;assert(call(91,&a)==2);v[2]=0;v[3]=0;assert(call(91,&a)==2);v[3]=1;
v[4]=14;assert(call(91,&a)==2);v[4]=5;v[6]=0;assert(call(91,&a)==2);v[6]=1;
process.uid=1;assert(call(91,&a)==1);process.uid=0;process.ppid=6;assert(call(91,&a)==1);process.ppid=1;
actor="other";assert(call(91,&a)==1);actor="m39-probe";
a.scalarOutputCount=1;assert(call(91,&a)==2);a.scalarOutputCount=0;
a.structureInputDescriptor=(void*)1;assert(call(91,&a)==2);a.structureInputDescriptor=nullptr;
a.structureOutputDescriptor=(void*)1;assert(call(91,&a)==2);a.structureOutputDescriptor=nullptr;
a.structureInputSize=1;assert(call(91,&a)==2);a.structureInputSize=0;
a.structureOutputSize=1;assert(call(91,&a)==2);a.structureOutputSize=0;
assert(!memcmp(kept,gReaderDiag,sizeof kept)&&reports==1);
v[3]=2;v[4]=13;v[6]=7;assert(!call(91,&a)&&reports==2&&gReaderDiag[5]==13);
puts("M46C actual diagnostic selector: root/parent/name, scalar shape/bounds, rejection preserves retained snapshot PASS");}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);f=d/'test.cpp';f.write_text(prefix+'\n#include <initializer_list>\n'+helper+'\nstatic int call(unsigned selector,Args *a){\n'+handler+test)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(f),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
