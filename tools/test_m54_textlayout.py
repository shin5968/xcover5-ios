"""Real macOS CoreText layout renderer and actual submission code; framebuffer mocked.
SDK typing is also checked by the separate arm64 iOS target build.
"""
from pathlib import Path
import os, subprocess, tempfile
r=Path(__file__).resolve().parents[1]
(r/'out').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);c=d/'render.c';exe=d/'render'
 c.write_text(r'''#include <assert.h>
#include <stdlib.h>
#include "panel-textlayout.h"
int main(void){
 size_t n=720U*1480U;
 uint32_t *base=calloc(n+32,sizeof(*base));assert(base);uint32_t *p=base+16;
 for(unsigned i=0;i<16;i++)base[i]=base[n+16+i]=0x12345678;
 assert(!m54_load_layout());
 uint64_t hashes[16];
 for(unsigned f=0;f<16;f++){
  memset(p,0,n*4);assert(!m54_draw(p,f));
  for(unsigned i=0;i<16;i++)assert(base[i]==0x12345678&&base[n+16+i]==0x12345678);
  uint64_t h=14695981039346656037ULL;
  for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ULL;
  hashes[f]=h;for(unsigned j=0;j<f;j++)assert(hashes[j]!=h);
  if(f==7){FILE *image=fopen("out/m54-textlayout-preview.ppm","wb");assert(image);fprintf(image,"P6\n720 1480\n255\n");for(size_t k=0;k<n;k++){unsigned char rgb[3]={p[k]>>16,p[k]>>8,p[k]};assert(fwrite(rgb,1,3,image)==3);}assert(!fclose(image));}
 }
 CGDataProviderRef provider=m53ct.provider(NULL,m53_font_bytes,sizeof m53_font_bytes,NULL);assert(provider);
 CGFontRef graphics=m53ct.font(provider);assert(graphics);m53ct.provider_release(provider);
 CTFontRef font=m53ct.ctfont(graphics,28,NULL,NULL);assert(font);m53ct.font_release(graphics);
 CGColorSpaceRef space=m52cg.space();assert(space);
 CGContextRef c=m52cg.create(p,720,1480,8,2880,space,kCGImageAlphaPremultipliedFirst|kCGBitmapByteOrder32Little);assert(c);m52cg.space_release(space);
 const char *paragraph="CORETEXT WRAPS THIS PARAGRAPH INTO LINES USING AN EXPLICIT FONT AND THE AVAILABLE WIDTH EACH FRAME USES THE SAME TEXT WITH A DIFFERENT COLUMN WIDTH ALL CHARACTERS MUST FIT INSIDE THE FRAME AND EVERY GLYPH RUN MUST KEEP THE SUPPLIED FONT";
 unsigned narrow=0,wide=0,invalid=999;
 assert(!m54_paragraph(c,font,paragraph,360,500,&narrow));
 assert(!m54_paragraph(c,font,paragraph,510,500,&wide));assert(narrow>wide&&wide>=4);
 assert(m54_paragraph(c,font,paragraph,360,20,&invalid)==3&&invalid==0);
 assert(m54_paragraph(c,font,"",360,500,&invalid)==1);
 assert(m54_paragraph(c,font,"?",360,500,&invalid)==1);
 assert(m54_paragraph(c,font,paragraph,NAN,500,&invalid)==1);
 assert(m54_paragraph(c,font,paragraph,511,500,&invalid)==1);
 m52cg.release(c);CFRelease(font);
 free(base);return 0;
}''')
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(r/'tools'),str(c),'-o',str(exe),'-framework','CoreFoundation'],check=True)
 subprocess.run([str(exe)],check=True,timeout=45)
scope={'__file__':str(r/'tools/test_m49_userspace.py')}
s=(r/'tools/test_m49_userspace.py').read_text().split('\nwith tempfile.TemporaryDirectory()')[0]
exec(compile(s,'m49-mock-builder','exec'),scope)
stub=scope['stub'].replace('m48_baseline_main','m53_baseline_main').replace('return 70;','return 75;')
stub+='\nstatic void persistent_status(mach_port_t c,uint64_t out[7]){unsigned n=7;if(io.call(c,93,NULL,0,NULL,0,out,&n,NULL,NULL)||n!=7)fail(198,"m54_status");}\n'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m53-baseline.c').write_text(stub);exe=d/'test'
 (d/'scene.c').write_text((r/'tools/surface-textlayout.c').read_text())
 (d/'panel-textlayout.h').write_text('int m54_test_load(void);int m54_test_draw(uint32_t *,unsigned);\n#define m54_load_layout m54_test_load\n#define m54_draw m54_test_draw\n')
 (d/'render-wrapper.c').write_text('#include "'+str(r/'tools/panel-textlayout.h')+'"\nint m54_test_load(void){return m54_load_layout();}\nint m54_test_draw(uint32_t *p,unsigned f){return m54_draw(p,f); }\n')
 subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(d),'-I'+str(r/'tools'),str(d/'scene.c'),str(d/'render-wrapper.c'),'-o',str(exe),'-framework','CoreFoundation'],check=True)
 for fault,where in [(None,None),('M49_TEST_CORRUPT_SOURCE','m54_source_changed'),('M49_TEST_BAD_RESTORE','m54_close_restore'),('M49_TEST_PREMATURE','m54_premature_completion')]:
  env=os.environ.copy()
  if fault:env[fault]='1'
  p=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=45)
  assert p.returncode==(199 if fault else 76),(fault,p.returncode,p.stdout,p.stderr)
  if fault:assert where in p.stderr and 'M54 PASS:' not in p.stdout
  else:assert 'M54 PASS:16 composed frames/14 persistent copies;' in p.stdout and p.stdout.count('M54 LAYOUT PASS')==16
print('M54 real macOS CoreText layout: caller memory identity/geometry/BGRA/opaque coverage, guard canaries,16 distinct frames; actual submit/cleanup code and negative integrity/completion/restore gates PASS. Framebuffer mocked; iOS execution still requires device.')
