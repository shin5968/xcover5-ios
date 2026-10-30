"""Actual renderer bounds/composition plus actual scene submit/cleanup gates."""
from pathlib import Path
import os, subprocess, tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);c=d/'render.c';exe=d/'render'
 c.write_text(r'''#include <assert.h>
#include <stdlib.h>
#include <limits.h>
#include "panel-scene.h"
int main(void){
 size_t n=M51_W*M51_H;
 uint32_t *base=calloc(n+2,sizeof(*base));assert(base);uint32_t *p=base+1;
 base[0]=base[n+1]=0x12345678;
 m51_rect(p,-2,-3,4,5,7);assert(p[0]==7&&p[1]==7&&p[2]==0&&p[720]==7&&p[1440]==0);
 m51_rect(p,INT_MAX,INT_MAX,INT_MAX,INT_MAX,9);
 m51_rect(p,INT_MIN,INT_MIN,INT_MAX,INT_MAX,9);
 m51_rect(p,0,0,-1,20,9);assert(p[0]==7);
 m51_rect(p,719,1479,INT_MAX,INT_MAX,11);assert(p[n-1]==11);
 uint64_t hashes[16];
 for(unsigned f=0;f<16;f++){
  m51_scene(p,f);assert(base[0]==0x12345678&&base[n+1]==0x12345678);
  assert(p[0]==0xff101827U);assert(p[302*720+36]==0xff2563a8U);
  int x=150+(int)f*22,y=584+(int)(f%4)*12;
  assert(p[y*720+x]==0xff9050c8U); /* foreground wins overlap */
  assert(p[1440*720+36]==0xff38dfb4U);
  assert(p[1440*720+680]==0xff101827U);
  uint64_t h=14695981039346656037ULL;
  for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ULL;
  hashes[f]=h;for(unsigned j=0;j<f;j++)assert(hashes[j]!=h);
 }
 m51_scene(p,16);assert(p[584*720+150]==0xff9050c8U);
 free(base);return 0;
}''')
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(r/'tools'),str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=15)
# Reuse the established framework mock, executing the actual new orchestration.
scope={'__file__':str(r/'tools/test_m49_userspace.py')}
s=(r/'tools/test_m49_userspace.py').read_text().split('\nwith tempfile.TemporaryDirectory()')[0]
exec(compile(s,'m49-mock-builder','exec'),scope)
stub=scope['stub'].replace('m48_baseline_main','m50_baseline_main').replace('return 70;','return 72;')
stub+='\nstatic void persistent_status(mach_port_t c,uint64_t out[7]){unsigned n=7;if(io.call(c,93,NULL,0,NULL,0,out,&n,NULL,NULL)||n!=7)fail(190,"m51_status");}\n'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m50-baseline.c').write_text(stub);exe=d/'test'
 subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(d),'-I'+str(r/'tools'),str(r/'tools/surface-scene.c'),'-o',str(exe)],check=True)
 for fault,where in [(None,None),('M49_TEST_CORRUPT_SOURCE','m51_source_changed'),('M49_TEST_BAD_RESTORE','m51_close_restore'),('M49_TEST_PREMATURE','m51_premature_completion')]:
  env=os.environ.copy()
  if fault:env[fault]='1'
  p=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=15)
  assert p.returncode==(191 if fault else 73),(fault,p.returncode,p.stdout,p.stderr)
  if fault:assert where in p.stderr and 'M51 PASS:' not in p.stdout
  else:assert 'M51 PASS:16 composed frames/14 persistent copies;' in p.stdout
print('M51 actual renderer and submit code: clipping/extreme coordinates/canaries/z-order/16 distinct scenes, two surfaces, hash integrity, premature completion and failed restore rejection PASS; framework mocked, no device claim')
