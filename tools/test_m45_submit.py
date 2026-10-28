"""Execute actual M45 kernel selector body with bounded memory/lifetime mocks."""
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0076-xcover5-user-surface-submit.patch').read_text()
added=''.join(x[1:] for x in p.splitlines(True) if x.startswith('+') and not x.startswith('+++'))
body=added[added.index('    if (selector == 90) {'):]
if len(sys.argv)>1:
 s=(Path(sys.argv[1])/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text();assert body in s
 assert 'fPresentationSequence = 0;' in s
prefix=r'''
#include <stdint.h>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include <cstdio>
#define MINISURF_TABLE_SIZE 256
#define kIOReturnNotPrivileged 1
#define kIOReturnBadArgument 2
#define kIOReturnNotFound 3
#define kIOReturnNoMemory 4
#define kIOReturnError 5
#define kIOReturnSuccess 0
struct MiniIOSurface {struct {unsigned width=64,height=32,bytesPerRow=256,pixelFormat=0x42475241,allocSize=8192;}info;uint8_t *kpixels;void *client=nullptr;};
struct minisurf_client_ref{MiniIOSurface *surface;};
struct Args {unsigned scalarInputCount=2,scalarOutputCount=3;size_t structureInputSize=0,structureOutputSize=0;void *structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;uint64_t scalarInput[2]={1,1},scalarOutput[3]={};};
typedef int proc_t;static int uid=0,ppid=1,holds=0,owned=0,nomem=0,active=0,begin_fail=0,end_fail=0;static unsigned slept=0;static void *gSurfaceLock;
static MiniIOSurface surface;static minisurf_client_ref ref={&surface};
static proc_t current_proc_EXTERNAL(){return 1;}static int proc_getuid(proc_t){return uid;}static int proc_ppid(proc_t){return ppid;}static int proc_getpid(proc_t){return 6;}
static void proc_name(int,char *p,size_t n){snprintf(p,n,"m39-probe");}
static void IOLockLock(void*){}static void IOLockUnlock(void*){}
static void surfaceHold(MiniIOSurface*){holds++;}static void MiniIOSurfaceDrop(MiniIOSurface*){assert(holds>0);holds--;}
static void *IOMalloc(size_t n){if(nomem)return nullptr;active++;return malloc(n);}static void IOFree(void *p,size_t){active--;free(p);}
static void IOSleep(unsigned n){assert(holds==1);slept+=n;}
static void IOLog(const char*,...){}
extern "C" int xcover5_present_begin(const uint32_t *p,uint32_t*){assert(holds==1);assert(p!=(uint32_t*)surface.kpixels);assert(!memcmp(p,surface.kpixels,8192));return begin_fail;}
extern "C" int xcover5_present_end(const uint32_t*){assert(holds==1);return end_fail;}
class Client {public:unsigned fPresentationSequence=0;minisurf_client_ref *findRef(uint32_t id,bool){return owned&&id==1?&ref:nullptr;}
int call(unsigned selector,Args *args){
'''
test=r'''
return -99;}};
int main(){uint8_t pixels[8192];for(unsigned i=0;i<8192;i++)pixels[i]=i;surface.kpixels=pixels;Client c;Args a;
uid=501;assert(c.call(90,&a)==1);uid=0;ppid=2;assert(c.call(90,&a)==1);ppid=1;
assert(c.call(90,&a)==3);owned=1;a.scalarInput[0]=0;assert(c.call(90,&a)==2);a.scalarInput[0]=1;
a.scalarOutputCount=2;assert(c.call(90,&a)==2);a.scalarOutputCount=3;
a.structureInputSize=1;assert(c.call(90,&a)==2);a.structureInputSize=0;
surface.info.width=63;assert(c.call(90,&a)==3);surface.info.width=64;
nomem=1;assert(c.call(90,&a)==4);assert(!holds&&!active);nomem=0;
begin_fail=1;assert(c.call(90,&a)==5);assert(!holds&&!active&&!c.fPresentationSequence);begin_fail=0;
assert(c.call(90,&a)==0);assert(a.scalarOutput[0]==1&&a.scalarOutput[2]==0);
uint64_t hash=14695981039346656037ULL;for(unsigned i=0;i<8192;i++)hash=(hash^pixels[i])*1099511628211ULL;assert(a.scalarOutput[1]==hash);
assert(c.call(90,&a)==2);a.scalarInput[1]=2;assert(!c.call(90,&a));assert(c.fPresentationSequence==2);
a.scalarInput[1]=3;assert(c.call(90,&a)==2);assert(!holds&&!active&&slept==4000);
puts("M45 actual selector: caller/ABI/ref/shape/replay checks, allocation/copy failure cleanup, retained surface, snapshot checksum and two completions PASS");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.cpp').write_text(prefix+body+test)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-multichar','-fsanitize=undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)

