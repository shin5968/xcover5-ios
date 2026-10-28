"""Run actual full-panel kernel copy, ABI and allocation helper against guarded RAM."""
from pathlib import Path
import sys,tempfile,subprocess
r=Path(__file__).resolve().parents[1];patch=(r/'xnu/patches/0080-xcover5-full-panel-surface.patch').read_text()
def additions(name):
 p=patch.split('+++ b/'+name+'\n')[1].split('--- ')[0]
 return ''.join(x[1:] for x in p.splitlines(True) if x.startswith('+'))
h=additions('iokit/Kernel/arm/XCoverFullPanelABI.h')
c=additions('iokit/Kernel/arm/MiniIOSurface.cpp');helper=c[:c.index('  if(selector==5')].removesuffix('  }\n');branch=c[c.index('  if(selector==5'):]+'  }\n'
copy=additions('pexpert/arm/pe_serial.c')
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert h==(t/'iokit/Kernel/arm/XCoverFullPanelABI.h').read_text()
 assert helper in (t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text() and branch in (t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert copy in (t/'pexpert/arm/pe_serial.c').read_text()
prefix=r'''#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef int boolean_t;typedef uint64_t ppnum_t;typedef uint64_t addr64_t;
#define PAGE_SIZE 16384
#define PAGE_SHIFT 14
'''+(r/'tools/framebuffer/layout.h').read_text()+r'''
static struct xc_fb_layout xc_fb={0xfa000000,0x1400000,4262400,720,1480,2880};
static volatile uint32_t *fbcon_base;static unsigned xc_fb_stage=4,xc_fb_presenting,locked,fail_page;
static void *kernel_pmap;
static boolean_t xc_fb_lock(void){assert(!locked);locked=1;return 1;}
static void xc_fb_unlock(boolean_t e){assert(e&&locked);locked=0;}
static ppnum_t pmap_find_phys(void*p,addr64_t va){(void)p;uint64_t off=va-(uintptr_t)fbcon_base;
 if(fail_page&&off==PAGE_SIZE)return 0;return (xc_fb.physical+off)>>PAGE_SHIFT;}
'''
copytest=r'''
int main(void){size_t n=1065600;uint32_t *all=malloc((n+2)*4),*orig=malloc(n*4),*pixels=malloc(n*4),*saved=calloc(n,4);assert(all&&orig&&pixels&&saved);
 all[0]=0x12345678;all[n+1]=0x87654321;fbcon_base=all+1;
 for(size_t i=0;i<n;i++){all[i+1]=orig[i]=(uint32_t)i;pixels[i]=0xff000000U|(uint32_t)(i*31);}
 assert(xcover5_full_present_end(saved)==2);xc_fb_stage=3;assert(xcover5_full_present_begin(pixels,saved)==1);xc_fb_stage=4;
 xc_fb.width=719;assert(xcover5_full_present_begin(pixels,saved)==1);xc_fb.width=720;
 fail_page=1;assert(xcover5_full_present_begin(pixels,saved)==2);fail_page=0;
 assert(!memcmp(all+1,orig,n*4));xc_fb_presenting=1;assert(xcover5_full_present_begin(pixels,saved)==3);xc_fb_presenting=0;
 assert(!xcover5_full_present_begin(pixels,saved));assert(xc_fb_presenting&&xc_fb_full_presenting&&!locked);
 assert(!memcmp(all+1,pixels,n*4)&&!memcmp(saved,orig,n*4));assert(xcover5_full_present_begin(pixels,saved)==3);
 assert(!xcover5_full_present_end(saved));assert(!memcmp(all+1,orig,n*4));assert(!xc_fb_presenting&&!xc_fb_full_presenting&&!locked);
 assert(all[0]==0x12345678&&all[n+1]==0x87654321);free(all);free(orig);free(pixels);free(saved);
 puts("M48 actual full-panel copy: exact geometry/pages, exclusive display, all1065600 pixels and restore, edge canaries PASS");}
'''
# Separate harness uses real parser + allocation helper and actual dispatch branch.
kp=r'''#include <stdint.h>
#include <cstring>
#include <cstdlib>
#include <cassert>
#include <cstdio>
#define kIOReturnBadArgument 2
#define kIOReturnNoMemory 3
#define kIOReturnSuccess 0
#define kIOReturnError 4
using IOReturn=int;
struct MiniIOSurface{struct{unsigned width=720,height=1480,bytesPerRow=2880,pixelFormat=0x42475241,allocSize=4262400;}info;uint8_t*kpixels=nullptr;void*client=nullptr;};
static MiniIOSurface surface;static unsigned holds,allocs,calls,fail_alloc;static int begin_rc,end_rc,locked;
static MiniIOSurface*MiniIOSurfaceCopy(unsigned sid){if(sid!=1)return nullptr;holds++;return &surface;}
static void MiniIOSurfaceDrop(MiniIOSurface*){assert(holds==1);holds--;}
static void*IOMalloc(size_t n){calls++;if(calls==fail_alloc)return nullptr;allocs++;return malloc(n);}
static void IOFree(void*p,size_t){assert(allocs);allocs--;free(p);}
static void IOLog(const char*,...){}static void IOSleep(unsigned n){assert(n==2000&&holds==1);}
extern "C" int xcover5_full_present_begin(const uint32_t*p,uint32_t*s){assert(holds==1&&allocs==2&&!memcmp(p,surface.kpixels,4262400));s[0]=123;return begin_rc;}
extern "C" int xcover5_full_present_end(const uint32_t*s){assert(s[0]==123&&holds==1);return end_rc;}
static void IOLockLock(void*){assert(!locked);locked=1;}static void IOLockUnlock(void*){assert(locked);locked=0;}
struct Args{const void*structureInput=nullptr;size_t structureInputSize=0,structureOutputSize=0;unsigned scalarInputCount=0,scalarOutputCount=0;void*structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;};
'''
kt=r'''
 return 5;}};
static void word(uint8_t*b,unsigned off,unsigned n){memcpy(b+off,&n,4);}
int main(){uint8_t b[0x46c]={};word(b,0x50,1);word(b,0x54,1);word(b,0x104,1);
 word(b,0x6c,720);word(b,0x70,1480);word(b,0xcc,720);word(b,0xd0,1480);
 assert(xc_fb_full_swap_valid(b,sizeof b));assert(!xc_fb_swap_valid(b,sizeof b,1));assert(!xc_fb_full_swap_valid(nullptr,sizeof b));assert(!xc_fb_full_swap_valid(b,sizeof(b)-1));
 word(b,0xc4,1);assert(!xc_fb_full_swap_valid(b,sizeof b));word(b,0xc4,0);
 word(b,0x50,3);assert(!xc_fb_full_swap_valid(b,sizeof b));word(b,0x50,1);
 surface.kpixels=(uint8_t*)calloc(1,4262400);assert(surface.kpixels);
 for(unsigned at=1;at<=2;at++){calls=0;fail_alloc=at;assert(xcFullPanelSubmit(1,1)==3);assert(!holds&&!allocs);}fail_alloc=0;
 begin_rc=1;assert(xcFullPanelSubmit(1,1)==4);begin_rc=0;end_rc=1;assert(xcFullPanelSubmit(1,1)==4);end_rc=0;
 surface.info.width=719;assert(xcFullPanelSubmit(1,1)==2);surface.info.width=720;
 Client c;Args a;a.structureInput=b;a.structureInputSize=sizeof b;
 assert(c.call(5,&a)==2&&!c.fCompleted);c.fIssued=1;
 a.structureOutputDescriptor=(void*)1;assert(c.call(5,&a)==2&&!c.fCompleted);a.structureOutputDescriptor=nullptr;
 assert(!c.call(5,&a)&&c.fCompleted==1&&!locked&&!holds&&!allocs);assert(c.call(5,&a)==2);
 word(b,0x50,2);c.fIssued=2;assert(!c.call(5,&a)&&c.fCompleted==2&&!holds&&!allocs&&!locked);
 free(surface.kpixels);puts("M48 actual ABI/helper: truncation/geometry/state/replay rejection, both allocation failures and copy failures free resources PASS");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'XCoverFullPanelABI.h').write_text(h)
 abi=(r/'xnu/patches/0077-xcover5-standard-framebuffer-subset.patch').read_text().split('+++ b/iokit/Kernel/arm/XCoverFramebufferABI.h\n')[1].split('--- ')[0]
 abi=''.join(x[1:] for x in abi.splitlines(True) if x.startswith('+'))
 for name,source,compiler in [('copy',prefix+copy+copytest,'cc'),('helper',kp+abi+helper+'\nclass Client{public:void*fLock=nullptr;unsigned fIssued=0,fCompleted=0;int call(unsigned selector,Args*a){\n'+branch+kt,'c++')]:
  f=d/(name+('.c' if compiler=='cc' else '.cpp'));f.write_text(source)
  subprocess.run([compiler,'-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-multichar','-fsanitize=undefined','-I'+str(d),str(f),'-o',str(d/name)],check=True)
  subprocess.run([str(d/name)],check=True)
