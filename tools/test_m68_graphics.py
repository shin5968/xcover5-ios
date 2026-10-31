"""Compile actual M68 service bodies against owned IOKit/panel mocks; verify patch/source identity."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0092-xcover5-native-hackios-graphics.patch').read_text()
for source,target in [('native_abi.h','XCoverNativeFBABI.h'),('native_service.h','XCoverNativeFramebuffer.h'),('native_observation.h','XCoverFBObservation.h')]:
    section=p.split('+++ b/iokit/Kernel/arm/'+target+'\n')[1].split('--- ')[0]
    actual=''.join(line[1:] for line in section.splitlines(True) if line.startswith('+'))
    assert actual==(r/'tools/framebuffer'/source).read_text(),target
if len(sys.argv)>1:
    tree=Path(sys.argv[1]);directory=tree/'iokit/Kernel/arm'
    for source,target in [('native_abi.h','XCoverNativeFBABI.h'),('native_service.h','XCoverNativeFramebuffer.h'),('native_observation.h','XCoverFBObservation.h')]:
        assert (directory/target).read_text()==(r/'tools/framebuffer'/source).read_text()
    s=(directory/'MiniIOSurface.cpp').read_text()
    assert '#include "XCoverNativeFramebuffer.h"' in s and 'XCoverNativeFramebufferStart(provider);' in s
    assert 'class XCoverDiagnosticFramebuffer : public IOService' in s
    assert 'same task-based user client as HackiOS' in s
    assert 'if (proc_getuid(current_proc_EXTERNAL()) != 0) return false;' not in s
    assert 'if (proc_getuid(caller) != 0 || proc_ppid(caller) != 1 ||' in s and 'strcmp(name, "m39-probe")' in s
    assert 'if (selector != kSurfaceMethodCreate && selector != kSurfaceMethodLookup &&' not in s
    if '--source-only' in sys.argv:
        print('M68 actual applied native service/header/IOSurface admission identity PASS');sys.exit(0)
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    for source,target in [('native_abi.h','XCoverNativeFBABI.h'),('native_service.h','XCoverNativeFramebuffer.h'),('native_observation.h','XCoverFBObservation.h')]:
        (d/target).write_text((r/'tools/framebuffer'/source).read_text())
    (d/'test.cpp').write_text((r/'tools/framebuffer/native_host.cpp').read_text())
    subprocess.run(['c++','-std=c++17','-O1','-Wall','-Wextra','-Wno-multichar','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
