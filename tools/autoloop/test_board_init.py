"""Exercise the actual board-init body with register/side-effect mocks."""
from pathlib import Path
import subprocess
import tempfile
here=Path(__file__).resolve().parent
source=(here/'platform.c.inc').read_text()
body=source[source.index('void xcover5_autolog_init(void) {'):]
fixture=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
typedef uintptr_t vm_offset_t;
static int enabled=1,started,cmu_reads,dwc_reads,maps;
static uint32_t power=1,gate=1U<<21,id=0x5533330a;
static void PE_parse_boot_argn(const char *n,int *v,size_t s){(void)n;(void)s;*v=enabled;}
static vm_offset_t ml_io_map(vm_offset_t p,size_t n){(void)n;maps++;return p;}
static uint32_t usb_rd(vm_offset_t p,uint32_t off){
 if(p==0x11860000){assert(off==0x1c84);return power;}
 if(p==0x13400000){assert(off==0x203c||off==0x2040||off==0x200c||off==0x2010);cmu_reads++;return gate;}
 assert(p==0x13600000);assert(off==0xc120||off==0xc110||off==0xc200);dwc_reads++;return id;
}
static void xcover5_usb_gadget_start(vm_offset_t p){assert(p==0x13600000);started++;}
'''+body+r'''
static void reset(void){started=cmu_reads=dwc_reads=maps=0;enabled=1;power=1;gate=1U<<21;id=0x5533330a;}
int main(void){
 reset();xcover5_autolog_init();assert(started==1 && cmu_reads==4 && dwc_reads==3);
 reset();power=0;xcover5_autolog_init();assert(!started && !cmu_reads && !dwc_reads && maps==1);
 reset();power=0x10;xcover5_autolog_init();assert(!started && !cmu_reads && !dwc_reads);
 reset();power=0x11;xcover5_autolog_init();assert(started==1);
 reset();gate=0;xcover5_autolog_init();assert(!started && !dwc_reads && maps==2);
 reset();id=0;xcover5_autolog_init();assert(!started && dwc_reads==3);
 reset();enabled=0;xcover5_autolog_init();assert(!started && !maps);
 puts("AUTO actual board init: Exynos3830 power1 accepted; power-off/clock/identity guards prevent device access PASS (host only)");
}
'''
with tempfile.TemporaryDirectory() as d:
    d=Path(d);(d/'test.c').write_text(fixture)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(d/'test.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
