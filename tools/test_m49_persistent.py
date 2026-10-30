# Actual M49 parser/helper/dispatch/close and full copy under guarded host RAM.
from pathlib import Path
import ast,subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
def literal(file,name):
 m=ast.parse((r/file).read_text())
 return next(ast.literal_eval(n.value) for n in m.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
patch=(r/'xnu/patches/0082-xcover5-persistent-full-panel.patch').read_text()
def added(f):
 p=patch.split('+++ b/'+f+'\n')[1].split('--- ')[0]
 return ''.join(x[1:] for x in p.splitlines(True) if x.startswith('+'))
a=added('iokit/Kernel/arm/MiniIOSurface.cpp')
helper=a[:a.index(' IOLock *fLock;')].rstrip()+'\n'
close=a[a.index(' IOReturn clientClose('):a.index('  if(selector==93)')]
branches=a[a.index('  if(selector==93)'):]
copy=added('pexpert/arm/pe_serial.c')
old=(r/'xnu/patches/0080-xcover5-full-panel-surface.patch').read_text()
oldcopy=''.join(x[1:] for x in old.split('+++ b/pexpert/arm/pe_serial.c\n')[1].splitlines(True) if x.startswith('+'))
abi=(r/'xnu/patches/0077-xcover5-standard-framebuffer-subset.patch').read_text().split('+++ b/iokit/Kernel/arm/XCoverFramebufferABI.h\n')[1].split('--- ')[0]
abi=''.join(x[1:] for x in abi.splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);s=(t/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert helper in s and close in s and branches in s and copy in (t/'pexpert/arm/pe_serial.c').read_text()
 assert 'if(proc_getuid(p)!=0 || proc_ppid(p)!=1 || strcmp(name,"m39-probe"))return false;' in s
m=ast.parse((r/'tools/test_m48_fullpanel.py').read_text())
expr=next(n.value for n in m.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix=ast.literal_eval(expr.left.left)+(r/'tools/framebuffer/layout.h').read_text()+ast.literal_eval(expr.right)
ct=r'''
int main(void){size_t n=1065600;uint32_t *all=calloc(n+2,4),*orig=calloc(n,4),*pixels=calloc(n,4),*saved=calloc(n,4);assert(all&&orig&&pixels&&saved);
all[0]=123;all[n+1]=456;fbcon_base=all+1;
for(size_t i=0;i<n;i++)all[i+1]=orig[i]=(uint32_t)i;
assert(xcover5_full_present_update(pixels)==2);assert(xcover5_full_present_update(NULL)==1);
assert(!xcover5_full_present_begin(pixels,saved));
for(unsigned frame=0;frame<14;frame++){
 for(size_t i=0;i<n;i++)pixels[i]=(uint32_t)(i+frame*7919);
 assert(!xcover5_full_present_update(pixels));assert(xc_fb_presenting&&xc_fb_full_presenting&&!locked);
 assert(!memcmp((const void*)fbcon_base,pixels,n*4));assert(!memcmp(saved,orig,n*4));assert(all[0]==123&&all[n+1]==456);
}
assert(!xcover5_full_present_end(saved)&&!xc_fb_presenting&&!memcmp((const void*)fbcon_base,orig,n*4));
assert(xcover5_full_present_update(pixels)==2);free(all);free(orig);free(pixels);free(saved);
puts("M49 actual full copy:14 persistent updates, all pixels readback, original console preserved/restored, edge canaries PASS");}
'''
kp=literal('tools/test_m48_fullpanel.py','kp')
kp=kp.replace('static unsigned holds,allocs,calls,fail_alloc;static int begin_rc,end_rc,locked;',
 'static unsigned holds,allocs,calls,fail_alloc;static int begin_rc,end_rc,update_rc;static bool locks[3];static void *gSurfaceLock=(void*)1;')
x=kp.index('static void IOLockLock(');y=kp.index('struct Args',x)
kp=kp[:x]+r'''static void IOLockLock(void*p){unsigned i=(unsigned)(uintptr_t)p;assert(i<3&&!locks[i]);locks[i]=true;}
static void IOLockUnlock(void*p){unsigned i=(unsigned)(uintptr_t)p;assert(i<3&&locks[i]);locks[i]=false;}
extern "C" int xcover5_full_present_update(const uint32_t*p){assert(p&&holds==1);return update_rc;}
#define APPLE_KEXT_OVERRIDE
struct IOUserClient{static void free(){}};
'''+kp[y:]
kp=kp.replace('assert(s[0]==123&&holds==1);','assert(s[0]==123);')
kp=kp.replace('#define APPLE_KEXT_OVERRIDE','#define XC_FULL_BYTES 4262400U\nstatic void IOLockFree(void*){}\n#define APPLE_KEXT_OVERRIDE')
kp=kp.replace('unsigned scalarInputCount=0,scalarOutputCount=0;', 'unsigned scalarInputCount=0,scalarOutputCount=0;uint64_t *scalarOutput=nullptr;')
kt=r'''
 return 5;}};
static void word(uint8_t*b,unsigned off,unsigned n){memcpy(b+off,&n,4);}
int main(){uint8_t b[0x46c]={};word(b,0x50,3);word(b,0x54,1);word(b,0x104,1);
word(b,0x6c,720);word(b,0x70,1480);word(b,0xcc,720);word(b,0xd0,1480);
assert(xcPersistentSwapValid(b,sizeof b));assert(!xcPersistentSwapValid(nullptr,sizeof b));assert(!xcPersistentSwapValid(b,sizeof b-1));
for(unsigned off:{0x50u,0x54u,0x58u,0x64u,0xc4u,0x104u,0x108u}){uint8_t bad[sizeof b];memcpy(bad,b,sizeof b);word(bad,off,0xffffffffU);assert(!xcPersistentSwapValid(bad,sizeof b));}
word(b,0x50,2);assert(!xcPersistentSwapValid(b,sizeof b));word(b,0x50,17);assert(!xcPersistentSwapValid(b,sizeof b));word(b,0x50,3);
surface.kpixels=(uint8_t*)calloc(1,4262400);assert(surface.kpixels);
for(unsigned which=1;which<=2;which++){XCPersistentPanel p={};calls=0;fail_alloc=which;assert(xcPersistentSubmit(&p,6,1,3)==3);assert(!p.active&&!holds&&!allocs);}fail_alloc=0;
XCPersistentPanel p={};begin_rc=1;assert(xcPersistentSubmit(&p,6,1,3)==4&&!p.active&&!allocs);begin_rc=0;
Client c;Args a;a.structureInput=b;a.structureInputSize=sizeof b;
assert(c.call(5,&a)==2);c.fIssued=3;c.fCompleted=2;
a.structureOutputDescriptor=(void*)1;assert(c.call(5,&a)==2);a.structureOutputDescriptor=nullptr;
assert(!c.call(5,&a)&&c.fCompleted==3&&c.fPersistent.active&&allocs==1&&!holds);
assert(c.call(5,&a)==2);uint64_t state[7]={};Args query;query.scalarOutput=state;query.scalarOutputCount=7;
assert(!c.call(93,&query)&&state[1]==1&&!state[0]);query.scalarInputCount=1;assert(c.call(93,&query)==2);query.scalarInputCount=0;
for(unsigned id=4;id<=16;id++){word(b,0x50,id);c.fIssued=id;assert(!c.call(5,&a)&&c.fCompleted==id&&allocs==1&&!holds);}
assert(c.fPersistent.frames==14&&!c.clientClose()&&!allocs);assert(!c.call(93,&query)&&state[0]==1&&!state[1]&&state[2]==6&&state[3]==14&&state[4]==1&&!state[5]&&state[6]==16);
assert(!c.clientClose()&&gPersistentStats[0]==1);c.free();assert(gPersistentStats[0]==1&&!allocs);
Client fallback;fallback.fIssued=3;fallback.fCompleted=2;word(b,0x50,3);assert(!fallback.call(5,&a));fallback.free();assert(gPersistentStats[0]==2&&gPersistentStats[4]==2&&!allocs);
Client bad;bad.fIssued=3;bad.fCompleted=2;update_rc=1;assert(bad.call(5,&a)==4&&bad.fCompleted==2&&bad.fPersistent.failed&&!allocs);update_rc=0;
assert(gPersistentStats[0]==3&&gPersistentStats[4]==3);assert(bad.call(5,&a)==2);bad.free();
Client restore_bad;restore_bad.fIssued=3;restore_bad.fCompleted=2;assert(!restore_bad.call(5,&a));end_rc=1;assert(restore_bad.clientClose()==4&&!allocs);end_rc=0;
assert(gPersistentStats[0]==4&&gPersistentStats[5]==1);restore_bad.free();free(surface.kpixels);
puts("M49 actual parser/helper/dispatch/close:14 completions, no replay, allocation/copy/restore failures, single cleanup and free fallback PASS");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)
 wrapper='\nclass Client{public:void*fLock=(void*)2;uint32_t fIssued=0,fCompleted=0,fOwner=6;XCPersistentPanel fPersistent={};bool isInactive(){return false;}void terminate(){}\n'+close+'int call(unsigned selector,Args*a){\n'
 for name,source,compiler in [('copy',prefix+oldcopy+copy+ct,'cc'),('service',kp+'\n#include <initializer_list>\n'+abi+helper+wrapper+branches+kt,'c++')]:
  f=d/(name+('.c' if compiler=='cc' else '.cpp'));f.write_text(source)
  subprocess.run([compiler,'-std=c11' if compiler=='cc' else '-std=c++17','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-Wno-multichar','-fsanitize=undefined',str(f),'-o',str(d/name)],check=True)
  subprocess.run([str(d/name)],check=True)
