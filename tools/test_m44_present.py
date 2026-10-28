"""M44: execute actual framebuffer copy/restore functions against guarded host RAM."""
from pathlib import Path
import sys,tempfile,subprocess
r=Path(__file__).resolve().parents[1]
patch=(r/'xnu/patches/0075-xcover5-reversible-surface-present.patch').read_text()
# The standalone function block is appended verbatim to the patch.
start=patch.index('+int xcover5_present_begin(')
lines=patch[start:].splitlines(True)
body=''
for line in lines:
    if line.startswith('--- '):break
    if line.startswith('+'):body+=line[1:]
body=body[:body.rindex('#endif')]
if len(sys.argv)>1:
 t=Path(sys.argv[1]);s=(t/'pexpert/arm/pe_serial.c').read_text()
 assert body in s
 assert 'if (xc_fb_presenting)' in s and 'xcover5_log_byte(c); /* Keep capture' in s
 assert 'rv == 0x4000' in (t/'bsd/kern/kern_exit.c').read_text()
 assert 'IOSleep(2000)' in (t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
prefix='''#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef int boolean_t;typedef uint64_t ppnum_t;typedef uint64_t addr64_t;
#define PAGE_SIZE 16384
#define PAGE_SHIFT 14
'''+(r/'tools/framebuffer/layout.h').read_text()+'''
static struct xc_fb_layout xc_fb={0xfa000000,0x1400000,2880ULL*1480,720,1480,2880};
static volatile uint32_t *fbcon_base;
static unsigned xc_fb_stage=4,xc_fb_presenting,locked,fail_page;
static void *kernel_pmap;
static boolean_t xc_fb_lock(void){assert(!locked);locked=1;return 1;}
static void xc_fb_unlock(boolean_t e){assert(e&&locked);locked=0;}
static ppnum_t pmap_find_phys(void *p,addr64_t va){(void)p;
 uint64_t off=va-(uintptr_t)fbcon_base;
 if(fail_page && off==PAGE_SIZE)return 0;
 return (xc_fb.physical+off)>>PAGE_SHIFT;}
'''
test=r'''
int main(void){
 size_t words=xc_fb.used/4; uint32_t *all=malloc((words+2)*4),*original=malloc(words*4);
 uint32_t pixels[2048],saved[32768];assert(all&&original);
 all[0]=0x12345678;all[words+1]=0x87654321;fbcon_base=all+1;
 for(size_t i=0;i<words;i++)original[i]=all[i+1]=(uint32_t)i;
 for(unsigned i=0;i<2048;i++)pixels[i]=0xff000000|i;
 assert(xcover5_present_end(saved)==2);
 xc_fb_stage=3;assert(xcover5_present_begin(pixels,saved)==1);xc_fb_stage=4;
 fail_page=1;assert(xcover5_present_begin(pixels,saved)==2);fail_page=0;
 assert(!memcmp(original,all+1,words*4));
 assert(!xcover5_present_begin(pixels,saved));assert(xc_fb_presenting);
 assert(xcover5_present_begin(pixels,saved)==3);
 unsigned x0=(720-256)/2,y0=(1480-128)/2;
 for(unsigned y=0;y<1480;y++)for(unsigned x=0;x<720;x++){
  uint32_t expected=(x>=x0&&x<x0+256&&y>=y0&&y<y0+128)?pixels[((y-y0)/4)*64+(x-x0)/4]:original[y*720+x];
  assert(all[1+y*720+x]==expected);
 }
 assert(!xcover5_present_end(saved));assert(!xc_fb_presenting&&!locked);
 assert(!memcmp(original,all+1,words*4));
 assert(all[0]==0x12345678&&all[words+1]==0x87654321);
 assert(xcover5_present_begin(NULL,saved)==1);
 free(all);free(original);puts("M44 actual copy/restore + full-frame unchanged exterior + missing mapping + repeated begin + canaries PASS");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+body+test)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
