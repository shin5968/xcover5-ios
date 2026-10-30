"""Test actual downstream patch bytes and host save-before-reset protocol."""
from pathlib import Path
import subprocess
import sys
import tempfile
repo=Path(__file__).resolve().parents[2]
here=repo/'tools/autoloop'
patch=(repo/'xnu/patches/0062-xcover5-usb-autolog.patch').read_text()
def added(name):
    part=patch.split('+++ b/'+name+'\n',1)[1].split('--- ',1)[0]
    return ''.join(x[1:] for x in part.splitlines(True) if x.startswith('+'))
for target,source in [('bsd/dev/xcover5_auto_capture.h','capture.h'),('bsd/dev/xcover5_usb_descriptors.h','descriptors.h')]:
    assert added(target)==(here/source).read_text()
expected=(here/'platform.c.inc').read_text()+'\n'+(here/'usb_ep0.c.inc').read_text()+'\n#endif /* XCOVER5 */\n'
assert added('bsd/dev/xcover5_autolog.c')==expected
if len(sys.argv)>1:
    tree=Path(sys.argv[1])
    for name in ['bsd/dev/xcover5_auto_capture.h','bsd/dev/xcover5_usb_descriptors.h','bsd/dev/xcover5_autolog.c']:
        expected_applied=added(name)
        if name=='bsd/dev/xcover5_autolog.c':
            # Original0062/template bytes remain pinned above. M50 adds only
            # the registered orphan's intermediate-SIGKILL capture guard.
            update=(repo/'xnu/patches/0083-xcover5-panel-client-death.patch').read_text().split('+++ b/bsd/dev/xcover5_autolog.c\n')[1]
            extra=''.join(x[1:] for x in update.splitlines(True) if x.startswith('+') and not x.startswith('+++'))
            guard=extra[extra.index('    if(rv==9'):]
            expected_applied=expected_applied.replace('void xcover5_test_finish(proc_t p,int rv) {','extern int xcover5_expected_panel_death(proc_t);\nvoid xcover5_test_finish(proc_t p,int rv) {')
            expected_applied=expected_applied.replace('    printf("XCOVER5 AUTO TEST_END',guard+'    printf("XCOVER5 AUTO TEST_END')
        assert (tree/name).read_text()==expected_applied,name
    for name,marker in [('pexpert/arm/pe_serial.c','xcover5_log_byte(c);'),('bsd/kern/bsd_init.c','xcover5_autolog_init();'),('bsd/kern/kern_exit.c','xcover5_test_finish(p,rv);')]:
        assert (tree/name).read_text().count(marker)==1
with tempfile.TemporaryDirectory() as d:
    exe=Path(d)/'capture-test'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pthread',str(here/'test_capture.c'),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
subprocess.run([sys.executable,str(here/'test_collect.py')],check=True)
subprocess.run([sys.executable,str(here/'test_board_init.py')],check=True)
subprocess.run([sys.executable,str(here/'test_epcmd.py')],check=True)
print('AUTO exact patch/header integration and PC ACK gate tests PASS (host only)')
