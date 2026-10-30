"""Real macOS CoreGraphics renderer and actual submission code; framebuffer mocked.
SDK typing is also checked by the separate arm64 iOS target build.
"""
from pathlib import Path
import os, subprocess, tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);c=d/'render.c';exe=d/'render'
 c.write_text(r'''#include <assert.h>
#include <stdlib.h>
#include "panel-coregraphics.h"
int main(void){
 size_t n=720U*1480U;
 uint32_t *base=calloc(n+32,sizeof(*base));assert(base);uint32_t *p=base+16;
 for(unsigned i=0;i<16;i++)base[i]=base[n+16+i]=0x12345678;
 assert(!m52_load_cg());
 uint64_t hashes[16];
 for(unsigned f=0;f<16;f++){
  memset(p,0,n*4);assert(!m52_draw(p,f));
  for(unsigned i=0;i<16;i++)assert(base[i]==0x12345678&&base[n+16+i]==0x12345678);
  uint64_t h=14695981039346656037ULL;
  for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ULL;
  hashes[f]=h;for(unsigned j=0;j<f;j++)assert(hashes[j]!=h);
 }
 free(base);return 0;
}''')
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(r/'tools'),str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=45)
scope={'__file__':str(r/'tools/test_m49_userspace.py')}
s=(r/'tools/test_m49_userspace.py').read_text().split('\nwith tempfile.TemporaryDirectory()')[0]
exec(compile(s,'m49-mock-builder','exec'),scope)
stub=scope['stub'].replace('m48_baseline_main','m51_baseline_main').replace('return 70;','return 73;')
stub+='\nstatic void persistent_status(mach_port_t c,uint64_t out[7]){unsigned n=7;if(io.call(c,93,NULL,0,NULL,0,out,&n,NULL,NULL)||n!=7)fail(192,"m52_status");}\n'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m51-baseline.c').write_text(stub);exe=d/'test'
 (d/'scene.c').write_text((r/'tools/surface-coregraphics.c').read_text())
 (d/'panel-coregraphics.h').write_text('int m52_test_load(void);int m52_test_draw(uint32_t *,unsigned);\n#define m52_load_cg m52_test_load\n#define m52_draw m52_test_draw\n')
 (d/'render-wrapper.c').write_text('#include "'+str(r/'tools/panel-coregraphics.h')+'"\nint m52_test_load(void){return m52_load_cg();}\nint m52_test_draw(uint32_t *p,unsigned f){return m52_draw(p,f); }\n')
 subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(d),'-I'+str(r/'tools'),str(d/'scene.c'),str(d/'render-wrapper.c'),'-o',str(exe)],check=True)
 for fault,where in [(None,None),('M49_TEST_CORRUPT_SOURCE','m52_source_changed'),('M49_TEST_BAD_RESTORE','m52_close_restore'),('M49_TEST_PREMATURE','m52_premature_completion')]:
  env=os.environ.copy()
  if fault:env[fault]='1'
  p=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=45)
  assert p.returncode==(193 if fault else 74),(fault,p.returncode,p.stdout,p.stderr)
  if fault:assert where in p.stderr and 'M52 PASS:' not in p.stdout
  else:assert 'M52 PASS:16 composed frames/14 persistent copies;' in p.stdout and p.stdout.count('M52 DRAW PASS')==16
print('M52 real macOS CoreGraphics: caller memory identity/geometry/BGRA/opaque coverage, guard canaries,16 distinct frames; actual submit/cleanup code and negative integrity/completion/restore gates PASS. Framebuffer mocked; iOS execution still requires device.')
