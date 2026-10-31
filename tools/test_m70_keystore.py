"""Compile actual M70 service bodies and verify patched source identity."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
body=(r/'tools/keystore/service.h').read_text()
patch=(r/'xnu/patches/0094-xcover5-keystore-events.patch').read_text()
section=patch.split('+++ b/iokit/Kernel/arm/XCoverAppleKeyStore.h\n')[1]
assert ''.join(line[1:] for line in section.splitlines(True) if line.startswith('+'))==body
if len(sys.argv)>1:
    tree=Path(sys.argv[1]);d=tree/'iokit/Kernel/arm'
    assert (d/'XCoverAppleKeyStore.h').read_text()==body
    s=(d/'MiniIOSurface.cpp').read_text()
    assert s.count('#include "XCoverAppleKeyStore.h"')==1
    assert s.count('XCoverAppleKeyStoreStart();')==1
    assert s.index('XCoverNativeFramebufferStart(provider);')<s.index('XCoverAppleKeyStoreStart();')
    if '--source-only' in sys.argv:
        print('M70 actual applied service/header/startup identity PASS');sys.exit(0)
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);(d/'XCoverAppleKeyStore.h').write_text(body)
    (d/'test.cpp').write_text((r/'tools/keystore/host.cpp').read_text())
    subprocess.run(['c++','-std=c++17','-O1','-Wall','-Wextra','-Wno-sign-compare','-Wno-misleading-indentation','-fsanitize=undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
