"""Render the maintained autoloop sources into the downstream XNU patch.

Input is the exact target XNU tree with patches0001..0061 already applied.
"""
from pathlib import Path
import difflib
import sys
r=Path(__file__).resolve().parents[2]
tree=Path(sys.argv[1])
diff=[]
def add(name,before,after):
    diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                fromfile='a/'+name if before else '/dev/null',tofile='b/'+name,n=3))
name='pexpert/arm/pe_serial.c';before=(tree/name).read_text()
anchor='fbcon_transmit_data(uint8_t c)\n{\n'
assert before.count(anchor)==1
after=before.replace(anchor,anchor+'#if defined(XCOVER5)\n\textern void xcover5_log_byte(uint8_t);\n\txcover5_log_byte(c);\n#endif\n')
add(name,before,after)
name='bsd/kern/bsd_init.c';before=(tree/name).read_text()
anchor='\txcover5_mmc_dev_init();\n'
assert before.count(anchor)==1
after=before.replace(anchor,anchor+'#if defined(XCOVER5)\n\textern void xcover5_autolog_init(void);\n\txcover5_autolog_init();\n#endif\n')
add(name,before,after)
name='bsd/kern/kern_exit.c';before=(tree/name).read_text()
anchor='\tif (proc_getcsflags(p) & CS_KILLED) {\n'
assert before.count(anchor)==1
after=before.replace(anchor,'#if defined(XCOVER5)\n\textern void xcover5_test_finish(proc_t,int);\n\txcover5_test_finish(p,rv);\n#endif\n'+anchor)
add(name,before,after)
name='bsd/conf/files';before=(tree/name).read_text()
anchor='bsd/dev/xcmmc.c\t\t\tstandard\n'
assert before.count(anchor)==1
after=before.replace(anchor,anchor+'bsd/dev/xcover5_autolog.c\t\tstandard\n')
add(name,before,after)
source=(r/'tools/autoloop/platform.c.inc').read_text()+'\n'+(r/'tools/autoloop/usb_ep0.c.inc').read_text()+'\n#endif /* XCOVER5 */\n'
add('bsd/dev/xcover5_autolog.c','',source)
add('bsd/dev/xcover5_auto_capture.h','',(r/'tools/autoloop/capture.h').read_text())
add('bsd/dev/xcover5_usb_descriptors.h','',(r/'tools/autoloop/descriptors.h').read_text())
(r/'xnu/patches/0062-xcover5-usb-autolog.patch').write_text(''.join(diff))
