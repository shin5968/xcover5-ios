"""M46 actual standard selector state machine and bounded swap ABI host test."""
from pathlib import Path
import sys,subprocess,tempfile
r=Path(__file__).resolve().parents[1];p=(r/'xnu/patches/0077-xcover5-standard-framebuffer-subset.patch').read_text()
def added(name):
 part=p.split('+++ b/'+name+'\n')[1].split('--- ')[0]
 return ''.join(x[1:] for x in part.splitlines(True) if x.startswith('+'))
h=added('iokit/Kernel/arm/XCoverFramebufferABI.h');c=added('iokit/Kernel/arm/MiniIOSurface.cpp')
start=c.index('  IOLockLock(fLock);');end=c.index('\n }\n};',start);body=c[start:end]
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'iokit/Kernel/arm/XCoverFramebufferABI.h').read_text()==h
 s=(t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text();assert body in s
 assert 'strcmp(name,"m39-probe")' in s and 'proc_ppid(p)!=1' in s
 assert (t/'iokit/Kernel/arm/SweetPlatformExpert.cpp').read_text().count('XCoverFramebufferStart(this);')==1
prefix=r'''
#include <stdint.h>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include <cstdio>
#define kIOReturnUnsupported 1
#define kIOReturnBadArgument 2
#define kIOReturnNoMemory 3
#define kIOReturnSuccess 0
#define kIOReturnError 4
typedef int IOReturn;static int holds=0,active=0,nomem=0,slept=0,locked=0;
struct MiniIOSurface {struct{unsigned width=64,height=32,bytesPerRow=256,pixelFormat=0x42475241,allocSize=8192;}info;uint8_t *kpixels;void *client=nullptr;};
static MiniIOSurface surface;
struct Args {unsigned scalarInputCount=0,scalarOutputCount=0;uint64_t scalarInput[3]={},scalarOutput[2]={};const void *structureInput=nullptr;size_t structureInputSize=0,structureOutputSize=0;void *structureInputDescriptor=nullptr;};
static void IOLockLock(void*){assert(!locked);locked=1;}static void IOLockUnlock(void*){assert(locked);locked=0;}
static MiniIOSurface *MiniIOSurfaceCopy(unsigned id){if(id!=1)return nullptr;holds++;return &surface;}
static void MiniIOSurfaceDrop(MiniIOSurface*){assert(holds==1);holds--;}
static void *IOMalloc(size_t n){if(nomem)return nullptr;active++;return malloc(n);}static void IOFree(void *p,size_t){active--;free(p);}
static void IOLog(const char*,...){}static void IOSleep(unsigned ms){assert(holds==1);slept+=ms;}
static int xcover5_present_begin(const uint32_t *b,uint32_t*){assert(holds==1);assert(!memcmp(b,surface.kpixels,8192));return 0;}
static int xcover5_present_end(const uint32_t*){assert(holds==1);return 0;}
'''
suffix=r'''
class Client{public:void *fLock=nullptr;unsigned fIssued=0,fCompleted=0;
IOReturn call(unsigned selector,Args*a){
'''
test=r'''
}};
static void word(uint8_t*b,unsigned off,uint32_t n){memcpy(b+off,&n,4);}
int main(){uint8_t pixels[8192]={},swap[0x46c]={};surface.kpixels=pixels;Client c;Args a;
a.scalarOutputCount=2;assert(!c.call(8,&a));assert(a.scalarOutput[0]==720&&a.scalarOutput[1]==1480);
a.scalarOutputCount=0;a.scalarInputCount=3;a.scalarInput[0]=1;assert(c.call(6,&a));
a.scalarInputCount=0;a.scalarOutputCount=1;assert(!c.call(4,&a));assert(a.scalarOutput[0]==1);assert(c.call(4,&a));
a.scalarOutputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);assert(c.call(5,&a));assert(!c.fCompleted);
word(swap,0x50,1);word(swap,0x54,1);word(swap,0x104,1);word(swap,0x6c,64);word(swap,0x70,32);
word(swap,0xc4,232);word(swap,0xc8,676);word(swap,0xcc,256);word(swap,0xd0,128);
assert(!xc_fb_swap_valid(swap,sizeof(swap)-1,1));assert(!xc_fb_swap_valid(nullptr,sizeof(swap),1));
word(swap,0x58,2);assert(c.call(5,&a));word(swap,0x58,0);
nomem=1;assert(c.call(5,&a)==3);assert(!holds&&!active&&!c.fCompleted);nomem=0;
assert(!c.call(5,&a));assert(c.fCompleted==1&&!holds&&!active);assert(c.call(5,&a));
a.structureInput=nullptr;a.structureInputSize=0;a.scalarInputCount=3;a.scalarInput[0]=1;assert(!c.call(6,&a));a.scalarInput[0]=2;assert(c.call(6,&a));
a.scalarInputCount=0;a.scalarOutputCount=1;assert(!c.call(4,&a));assert(a.scalarOutput[0]==2);
word(swap,0x50,2);a.scalarOutputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);assert(!c.call(5,&a));
a.structureInputSize=0;a.scalarInputCount=3;a.scalarInput[0]=2;assert(!c.call(6,&a));a.scalarInputCount=0;a.scalarOutputCount=1;assert(c.call(4,&a));
assert(!holds&&!active&&!locked&&slept==4000);puts("M46 actual selectors: layout/truncation/multilayer rejection, no premature/future/replayed completion, retained surface and allocation cleanup, two real copy/wait state transitions PASS");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.cpp').write_text(prefix+h+suffix+body+test)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-multichar','-fsanitize=undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
