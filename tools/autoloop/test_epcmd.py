"""Exercise actual endpoint command body with sleeping-PHY register model."""
from pathlib import Path
import subprocess,tempfile
here=Path(__file__).resolve().parent
s=(here/'usb_ep0.c.inc').read_text()
body=s[s.index('static int\nud_epcmd('):s.index('/* One TRB')]
defines='\n'.join(x for x in s.splitlines() if x.startswith('#define '))
fixture=defines+'\n#include <stdint.h>\n#include <stdio.h>\n#include <assert.h>\n\nstatic uint32_t phy,original,command;\nstatic int mode,issued,reads,phy_writes;\nstatic uint32_t dwc_rd(uint32_t off){\n if(off==GUSB2PHYCFG)return phy;\n if(off==DSTS)return 0;\n assert(off==DEPCMD(0)||off==DEPCMD(1));reads++;\n if(mode==2)return command;\n if(mode==1)return 1U<<12;\n /* Completion requires both sleep bits clear; model unrelated HW update. */\n assert(!(phy&USB2_CMD_SLEEP));phy|=1U<<20;return 0;\n}\nstatic void dwc_wr(uint32_t off,uint32_t v){\n if(off==GUSB2PHYCFG){phy=v;phy_writes++;return;}\n if(off==DEPCMD(0)||off==DEPCMD(1)){\n  assert(!(phy&USB2_CMD_SLEEP));issued++;command=v;return;\n }\n assert(off==DEPCMDPAR0(0)||off==DEPCMDPAR1(0)||off==DEPCMDPAR2(0)||\n        off==DEPCMDPAR0(1)||off==DEPCMDPAR1(1)||off==DEPCMDPAR2(1));\n}\nstatic void delay(unsigned n){assert(n==1);}\n'+body+'\nstatic void reset(uint32_t bits,int m){mode=m;issued=reads=phy_writes=0;original=phy=0x40102400U|bits;}\nint main(void){\n const uint32_t cases[]={0,1U<<6,1U<<8,USB2_CMD_SLEEP};\n for(unsigned i=0;i<4;i++){\n  reset(cases[i],0);assert(ud_epcmd(i%2,1,0,0,0)==0);assert(issued==1);\n  assert(phy==(original|(1U<<20)));assert(phy_writes==(cases[i]?2:0));\n  reset(cases[i],1);assert(ud_epcmd(0,1,0,0,0)==-1);assert(phy==original);\n  reset(cases[i],2);assert(ud_epcmd(0,1,0,0,0)==-1);assert(phy==original&&reads==1001);\n }\n puts("AUTO actual endpoint command: sleep bits clear at issue, preserved unrelated bits, restore on success/status/timeout PASS (host only)");\n}\n'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/"test.c").write_text(fixture)
 subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",str(d/"test.c"),"-o",str(d/"test")],check=True)
 subprocess.run([str(d/"test")],check=True)
