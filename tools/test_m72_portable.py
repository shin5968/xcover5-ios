"""Exercise imported bodies and check the exact applied kernel source, not a model."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1]
vendor=R/'third_party/hackios-portable'
origin=json.loads((vendor/'ORIGIN.json').read_text())
for item in origin['files']:
    data=(vendor/item['path']).read_bytes()
    assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item
expected=json.loads((vendor/'APPLIED.json').read_text())
if len(sys.argv)>1:
    tree=Path(sys.argv[1])
    for path,digest in expected.items():
        assert hashlib.sha256((tree/path).read_bytes()).hexdigest()==digest,path
    for src,dst in [('input.c','bsd/dev/xcover_input.c'),('input.h','bsd/dev/xcover_input.h'),('network.h','iokit/Kernel/arm/XCoverNetworkStack.h'),('filesystems.c','bsd/dev/xcover_filesystems.c')]:
        assert (R/'tools/compat'/src).read_bytes()==(tree/dst).read_bytes(),dst
    source=(tree/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
    assert source.count(' XCoverNetworkStackStart();')==1
    assert 'uint64_t planeBytes = (uint64_t)p->bytesPerRow' in source
    assert 'alloc < needed || alloc == 0 || alloc > MINISURF_MAX_ALLOC' in source
    assert 'const uint32_t createdAlloc = s->info.allocSize;' in source
    if '--source-only' in sys.argv:
        print('M72 applied source identities, retained safety/lifetime fixes, startup PASS');sys.exit(0)
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)
    # The actual registration body must match the two drivers' directory ABI.
    body=(R/'tools/compat/filesystems.c').read_text()
    body='\n'.join(line for line in body.splitlines() if not line.startswith('#include'))
    fixture='''
#include <stdio.h>
#include <string.h>
#include <assert.h>
struct vfsops{int id;}apfs_vfsops={1},ramfs_vfsops={2};
struct vnodeopv_desc{int id;};
const struct vnodeopv_desc apfs_vnodeop_opv_desc={1},ramfs_vnodeop_opv_desc={2};
typedef int vfstable_t;
#define VFS_TBLNOTYPENUM 1
#define VFS_TBL64BITREADY 2
#define VFS_TBLLOCALVOL 4
#define VFS_TBLGENERICMNTARGS 8
#define VFS_TBLTHREADSAFE 16
#define VFS_TBLNATIVEXATTR 32
#define VFS_TBLREADDIR_EXTENDED 64
#define VFS_TBLVNOP_PAGEINV2 128
#define VFS_TBLVNOP_PAGEOUTV2 256
struct vfs_fsentry{struct vfsops*vfe_vfsops;int vfe_vopcnt;struct vnodeopv_desc**vfe_opvdescs;unsigned vfe_flags;char vfe_fsname[32];};
static int registered;
static void strlcpy(char*d,const char*s,size_t n){snprintf(d,n,"%s",s);}
static int vfs_fsadd(struct vfs_fsentry*e,int*h){
 assert(e->vfe_vopcnt==1&&e->vfe_flags==(447U|(registered==0?64U:0U)));
 assert(e->vfe_vfsops==(registered==0?&apfs_vfsops:&ramfs_vfsops));
 assert(e->vfe_opvdescs[0]==(registered==0?&apfs_vnodeop_opv_desc:&ramfs_vnodeop_opv_desc));
 assert(!strcmp(e->vfe_fsname,registered==0?"apfs":"ramfs"));*h=++registered;return 0;
}
'''+body+'''
int main(){xcover_filesystems_register();assert(registered==2);puts("M75 actual registration: APFS extended, RAMFS classic dirent, other flags unchanged PASS");}
'''
    (d/'registration.c').write_text(fixture)
    subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(d/'registration.c'),'-o',str(d/'registration-test')],check=True)
    subprocess.run([str(d/'registration-test')],check=True)
    for src,dst in [('input.c','input.c'),('input.h','xcover_input.h'),('input_host.c','test.c')]:
        (d/dst).write_bytes((R/'tools/compat'/src).read_bytes())
    subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Wno-format','-Wno-unused-variable','-fsanitize=undefined',str(d/'test.c'),'-o',str(d/'input-test')],check=True)
    subprocess.run([str(d/'input-test')],check=True)
    # Reuse the established IOKit mock's lifetime semantics, include the actual new service.
    mock=(R/'tools/keystore/host.cpp').read_text().split('struct IOMemoryDescriptor')[0]
    mock=mock.replace('static int live=0,port_releases=0;','static int live=0;')
    mock+='''
struct IOUserClient:IOService{virtual IOReturn clientClose(){return 0;}virtual IOReturn setProperties(OSObject*){return 0;}};
static int proc_selfpid(){return 6;}
#define XC72_HOST_TEST 1
#include "network.h"
int main(){resources=new IOService;int before=live;
have_resources=false;XCoverNetworkStackStart();assert(live==before);have_resources=true;
fail_start=true;XCoverNetworkStackStart();assert(live==before&&resources->children.empty());fail_start=false;
XCoverNetworkStackStart();assert(resources->children.size()==1);auto*s=dynamic_cast<IONetworkStack*>(resources->children[0]);
assert(s&&s->name=="IONetworkStack"&&s->client=="IONetworkStackUserClient"&&s->registered);
auto*c=new IONetworkStackUserClient;assert(c->start(s));assert(c->setProperties(nullptr)==kIOReturnUnsupported);assert(!c->clientClose()&&c->inactive);c->release();resources->release();assert(!live);
puts("M72 actual network: IOResources discovery identity, failed startup cleanup, open, unsupported naming, close/lifetimes PASS");}
'''
    (d/'network.h').write_bytes((R/'tools/compat/network.h').read_bytes());(d/'network.cpp').write_text(mock)
    subprocess.run(['c++','-std=c++17','-O1','-Wall','-Wextra','-fsanitize=undefined',str(d/'network.cpp'),'-o',str(d/'network-test')],check=True)
    subprocess.run([str(d/'network-test')],check=True)
    # Upstream's test link command omits new zbitmap/SHA dependencies: supply both here.
    src=vendor/'xnu/files/bsd/miscfs/apfs';tests=vendor/'tools/apfs'
    subprocess.run(['cc','-std=c11','-O1','-w','-I'+str(tests/'host-shim'),'-c',str(src/'apfs_deflate.c'),'-o',str(d/'deflate.o')],check=True)
    subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-g','-fsanitize=undefined','-I'+str(src),str(tests/'test_fetch.c'),str(src/'apfs_zbitmap.c'),str(d/'deflate.o'),'-lz','-lcrypto','-pthread','-o',str(d/'fetch-test')],check=True)
    subprocess.run([str(d/'fetch-test')],check=True)
    subprocess.run(['cc','-std=c11','-I'+str(src),str(tests/'fmt_check.c'),'-o',str(d/'format-test')],check=True)
    (d/'format.txt').write_bytes(subprocess.check_output([str(d/'format-test')]))
    subprocess.run([sys.executable,str(tests/'test_format.py'),str(d/'format.txt')],check=True)
    subprocess.run([sys.executable,str(tests/'test_sparse.py')],check=True)
print('M72 pinned vendor/actual portable driver/parser tests PASS')
