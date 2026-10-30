"""Actual UI identity matcher and actual post-validation hook placement."""
from pathlib import Path
import sys,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0086-xcover5-pinned-ui-platform.patch').read_text()
header=''.join(x[1:] for x in p.split('+++ b/bsd/kern/xcover5_ui_platform.h\n')[1].splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'bsd/kern/xcover5_ui_platform.h').read_text()==header
 s=(t/'bsd/kern/ubc_subr.c').read_text();hook='unsigned int ui_identity=xcover5_ui_platform(tmp_blob.csb_cdhash,cs_flags,platform);'
 assert s.count('#include "xcover5_ui_platform.h"')==1 and s.count(hook)==1
 validation=s.index('error = mac_vnode_check_signature(');failure=s.index('if (error != 0)',validation)
 out=s.index('goto out;',failure);identity=s.index(hook);publish=s.index('tmp_blob.csb_flags = cs_flags;',identity)
 assert validation<failure<out<identity<publish
 assert 'cs_flags |= CS_PLATFORM_BINARY | CS_SIGNED;' in s[identity:publish]
 assert 'XCOVER5 M56 PINNED_UI' in s[identity:publish]
 if '--source-only' in sys.argv:
  print('M56 exact applied header and unique classification after successful MACF validation, before published flags PASS');raise SystemExit(0)
test=r'''
#include <assert.h>
#include <string.h>
int main(void){
 unsigned char good[2][20]={
 {0x45,0x3a,0xe2,0xe6,0x05,0x7a,0xcb,0x2d,0xea,0x0c,0x5a,0xe8,0xba,0x09,0x73,0x07,0x7e,0xa3,0xea,0xb1},
 {0x11,0x62,0x7e,0xea,0x9a,0x12,0x6a,0x45,0xb9,0xa2,0xb4,0xab,0xd3,0x1d,0x6c,0xaf,0xd5,0x9d,0x71,0x44}};
 assert(!xcover5_ui_platform(NULL,2,2));
 for(unsigned row=0;row<2;row++){
  assert(xcover5_ui_platform(good[row],2,2)==row+1);
  assert(xcover5_ui_platform(good[row],0xffffffffU,2)==row+1);
  for(unsigned platform=0;platform<16;platform++)if(platform!=2)assert(!xcover5_ui_platform(good[row],2,platform));
  for(unsigned flags=0;flags<256;flags++)assert(xcover5_ui_platform(good[row],flags,2)==((flags&2)?row+1:0));
  for(unsigned bit=0;bit<160;bit++){
   unsigned char bad[20];memcpy(bad,good[row],20);bad[bit/8]^=1U<<(bit%8);
   assert(!xcover5_ui_platform(bad,2,2));
  }
 }
 unsigned char zero[20]={0};assert(!xcover5_ui_platform(zero,2,2));return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(header+test)
 subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
print('M56 actual exact two identities:320 single-bit mismatches, wrong platforms/flags/null/unrelated hashes rejected; no name/path matching PASS')
