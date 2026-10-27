"""Exercise actual M42 geometry guard; optional applied-kernel integration checks."""
from pathlib import Path
import subprocess
import sys
import tempfile

r = Path(__file__).resolve().parents[1]
h = (r / 'tools/framebuffer/layout.h').read_text()
probe = None
patch = (r / 'xnu/patches/0073-xcover5-framebuffer-contract.patch').read_text()
part = patch.split('+++ b/pexpert/arm/xcover5_fb_layout.h\n', 1)[1].split('--- a/', 1)[0]
assert ''.join(line[1:] for line in part.splitlines(True) if line.startswith('+')) == h
if len(sys.argv) > 1:
    tree = Path(sys.argv[1])
    assert (tree / 'pexpert/arm/xcover5_fb_layout.h').read_text() == h
    serial = (tree / 'pexpert/arm/pe_serial.c').read_text()
    assert 'size != 16' in serial and 'size != 4' in serial
    assert 'if (!xc_fb_layout_valid(&xc_fb)) return;' in serial
    assert 'pmap_find_phys(kernel_pmap' in serial
    assert 'vinfo.v_baseaddr =' not in serial.replace('vinfo.v_baseaddr ==', '')
    assert (tree / 'bsd/kern/kern_exit.c').read_text().count('xcover5_framebuffer_report();') == 1
    start = serial.index('static void\nfbcon_probe(void)')
    end = serial.index('\n#if defined(XCOVER5)\n/* Late read-only report:', start)
    probe = serial[start:end]

source = '#include <stdint.h>\n#include <assert.h>\n#include <stdio.h>\n' + h + r'''
int main(void) {
    struct xc_fb_layout good={0xfa000000ULL,0x1400000,2880ULL*1480,720,1480,2880}, f;
    assert(xc_fb_layout_valid(&good));
    f=good; f.reserved=f.used; assert(xc_fb_layout_valid(&f));
    f.reserved--; assert(!xc_fb_layout_valid(&f));
    f=good; f.physical=0; assert(!xc_fb_layout_valid(&f));
    f=good; f.physical=UINT64_MAX-15; assert(!xc_fb_layout_valid(&f));
    f=good; f.physical+=4; assert(!xc_fb_layout_valid(&f));
    f=good; f.reserved=0; assert(!xc_fb_layout_valid(&f));
    f=good; f.reserved++; assert(!xc_fb_layout_valid(&f));
    f=good; f.used--; assert(!xc_fb_layout_valid(&f));
    f=good; f.width=UINT32_MAX; assert(!xc_fb_layout_valid(&f));
    f=good; f.height=UINT32_MAX; f.used=(uint64_t)f.stride*f.height; assert(!xc_fb_layout_valid(&f));
    f=good; f.stride=UINT32_MAX; f.used=(uint64_t)f.stride*f.height; assert(!xc_fb_layout_valid(&f));
    for (uint32_t w=0;w<8;w++) {f=good; f.width=w; assert(!xc_fb_layout_valid(&f));}
    for (uint32_t y=0;y<16;y++) {f=good; f.height=y; f.used=(uint64_t)f.stride*y; assert(!xc_fb_layout_valid(&f));}
    for (uint32_t s=2876;s<2884;s++) {
        f=good; f.stride=s; f.used=(uint64_t)s*f.height;
        assert(xc_fb_layout_valid(&f)==(s==2880));
    }
    /* Oversized row padding and geometry must never evade the 64-bit bound. */
    for (uint32_t w=8;w<=4096;w+=29) for(uint32_t y=16;y<=4096;y+=31) {
        f=good; f.width=w; f.height=y; f.stride=w*4; f.used=(uint64_t)f.stride*y;
        assert(xc_fb_layout_valid(&f)==(f.used<=f.reserved));
    }
    puts("M42 actual geometry guard: valid Samsung layout, short reservation, physical allowlist, row bounds, integer extremes and dimension matrix PASS (host only)");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / 'test.c').write_text(source)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined', str(d / 'test.c'), '-o', str(d / 'test')], check=True)
    subprocess.run([str(d / 'test')], check=True)
    if probe:
        mock = '#include <stdint.h>\n#include <string.h>\n#include <assert.h>\n#include <stdio.h>\n#define XCOVER5 1\n' + h + r'''
typedef int DTEntry;
enum {kSuccess=0};
static struct xc_fb_layout xc_fb;
static unsigned xc_fb_stage;
static volatile uint32_t *fbcon_base;
static uint32_t fbcon_width,fbcon_height,fbcon_stride;
static int sweet_fbcon_serial_functions;
static unsigned maps,registered,reg_size,width_size,height_size,stride_size;
static int map_fail,find_fail;
static uint64_t reg_data[2]={0xfa000000ULL,0x1400000};
static uint32_t w=720,h=1480,s=2880;
static int SecureDTFindEntry(const char *key,const char *name,DTEntry *out) {
    (void)key;(void)name;*out=1;return find_fail?1:0;
}
static int SecureDTGetProperty(DTEntry e,const char *name,const void **out,unsigned *size) {
    (void)e;
    if(!strcmp(name,"reg")){*out=reg_data;*size=reg_size;}
    else if(!strcmp(name,"width")){*out=&w;*size=width_size;}
    else if(!strcmp(name,"height")){*out=&h;*size=height_size;}
    else if(!strcmp(name,"stride")){*out=&s;*size=stride_size;}
    else return 1;
    return 0;
}
static void sweet_early_mark(unsigned n,const char *label){(void)n;(void)label;}
static uintptr_t ml_io_map_wcomb(uint64_t pa,uint64_t size){
    assert(pa==reg_data[0]&&size==reg_data[1]);maps++;return map_fail?0:0x12340000;
}
static void register_serial_functions(void *p){assert(p==&sweet_fbcon_serial_functions);registered++;}
static void reset(void){
    memset(&xc_fb,0,sizeof(xc_fb));xc_fb_stage=maps=registered=0;fbcon_base=0;
    reg_size=16;width_size=height_size=stride_size=4;map_fail=find_fail=0;
    reg_data[0]=0xfa000000ULL;reg_data[1]=0x1400000;w=720;h=1480;s=2880;
}
''' + probe + r'''
int main(void){
    reset();fbcon_probe();assert(maps==1&&registered==1&&xc_fb_stage==4);
    assert(fbcon_width==720&&fbcon_height==1480&&fbcon_stride==2880);
    for(unsigned n=0;n<=24;n++){
        if(n==16)continue;reset();reg_size=n;fbcon_probe();assert(!maps&&!registered&&xc_fb_stage==1);
    }
    for(unsigned property=0;property<3;property++)for(unsigned n=0;n<=8;n++){
        if(n==4)continue;reset();
        if(property==0)width_size=n;else if(property==1)height_size=n;else stride_size=n;
        fbcon_probe();assert(!maps&&!registered&&xc_fb_stage==1);
    }
    reset();reg_data[1]=64;fbcon_probe();assert(!maps&&!registered&&xc_fb_stage==2);
    reset();w=UINT32_MAX;fbcon_probe();assert(!maps&&!registered&&xc_fb_stage==2);
    reset();find_fail=1;fbcon_probe();assert(!maps&&!registered&&xc_fb_stage==1);
    reset();map_fail=1;fbcon_probe();assert(maps==1&&!registered&&xc_fb_stage==3);
    puts("M42 applied fbcon_probe: truncated/oversized ADT properties, missing node, bad geometry and mapping failure rejected before registration PASS (host only)");
}
'''
        (d / 'probe.c').write_text(mock)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation', '-fsanitize=undefined', str(d / 'probe.c'), '-o', str(d / 'probe')], check=True)
        subprocess.run([str(d / 'probe')], check=True)
