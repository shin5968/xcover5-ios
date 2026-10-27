"""Actual port bounds and applied-source integration; no device emulation claim."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
h=(r/'tools/surface/bounds.h').read_text()
p=(r/'xnu/patches/0074-xcover5-iosurface-bringup.patch').read_text()
part=p.split('+++ b/iokit/Kernel/arm/XCoverSurfaceBounds.h\n')[1].split('--- a/')[0]
assert ''.join(x[1:] for x in part.splitlines(True) if x.startswith('+'))==h
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'iokit/Kernel/arm/XCoverSurfaceBounds.h').read_text()==h
 c=(t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert 'loader_log_line(' not in c and 'gSurfaceClearing' not in c
 assert 'if (!xcSurfaceValidateProps(props)) return NULL;' in c
 assert 'if (proc_getuid(current_proc_EXTERNAL()) != 0) return false;' in c
 assert 'if (fRefCount >= 64) return NULL;' in c
 assert 'gSurfaceWired += bytes;' in c and 'gSurfaceWired-=bytes;' in c
 assert 's->memory = surfaceMemory(' in c
 assert (t/'iokit/conf/files.arm64').read_text().count('arm/MiniIOSurface.cpp')==1
 assert (t/'iokit/Kernel/arm/SweetPlatformExpert.cpp').read_text().count('MiniIOSurfaceStart(this);')==1
 assert (t/'bsd/kern/kern_exit.c').read_text().count('xcover5_surface_report();')==1
c='#include <stdint.h>\n#include <stdbool.h>\n#include <assert.h>\n#include <stdio.h>\n#define PAGE_SIZE 16384ULL\n'+h+r'''
int main(void){
 assert(xc_surface_shape(64,32,4,256,8192));
 assert(xc_surface_shape(720,1480,4,2880,4262400));
 assert(!xc_surface_shape(0,32,4,256,8192));
 assert(!xc_surface_shape(64,0,4,256,8192));
 assert(!xc_surface_shape(UINT64_MAX,32,4,0,0));
 assert(!xc_surface_shape(64,UINT64_MAX,4,0,0));
 assert(!xc_surface_shape(2049,32,4,0,0));
 assert(!xc_surface_shape(64,32,UINT64_MAX,0,0));
 assert(!xc_surface_shape(64,32,4,255,8192));
 assert(!xc_surface_shape(64,32,4,256,8191));
 assert(!xc_surface_shape(64,32,4,256,9ULL<<20));
 assert(!xc_surface_reservable(UINT64_MAX,16384));
 assert(!xc_surface_reservable(0,UINT64_MAX));
 assert(!xc_surface_reservable(0,0));
 assert(xc_surface_reservable(0,XC_SURFACE_MAX_ALLOC+PAGE_SIZE));
 assert(!xc_surface_reservable(XC_SURFACE_BUDGET,1));
 uint64_t used=0,n=XC_SURFACE_MAX_ALLOC+PAGE_SIZE;
 for(unsigned i=0;i<3;i++){assert(xc_surface_reservable(used,n));used+=n;}
 assert(!xc_surface_reservable(used,n));
 used-=n;assert(xc_surface_reservable(used,n));
 for(uint64_t w=1;w<=2048;w+=13)for(uint64_t h=1;h<=2048;h+=29){
   uint64_t row=(w*4+63)&~63ULL;
   assert(xc_surface_shape(w,h,4,0,0)==(row*h<=XC_SURFACE_MAX_ALLOC));
 }
 puts("M43 actual bounds: BGRA row/size arithmetic, integer extremes, reservation capacity/release and dimension matrix PASS (host only)");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(c)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
