"""Execute actual M48 orchestration; prior milestones and framework are mocked."""
from pathlib import Path
import ast,subprocess,tempfile,os
r=Path(__file__).resolve().parents[1]
m=ast.parse((r/'tools/test_m47_sequence.py').read_text())
stub=next(ast.literal_eval(n.value) for n in m.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stub' for t in n.targets))
stub=stub.replace('uint32_t p[2048]','uint32_t p[1065600]').replace('typedef struct{double x,y,width,height;}FBRect;','typedef struct{double x,y,width,height;}FBRect;typedef struct{double width,height;}FBSize;')
stub=stub.replace('d->done==16&&d->issued==16','d->done==2&&d->issued==2').replace('d->issued<16','d->issued<2').replace('M47_TEST_CORRUPT_SOURCE','M48_TEST_CORRUPT_SOURCE')
stub=stub.replace('static CFMutableDictionaryRef properties(void)',r'''#define CFSTR(s) (s)
static unsigned property_bits;
static void number(void*d,const char*n,int64_t v){assert(d==(void*)1);
 if(!strcmp(n,"IOSurfaceWidth")){assert(v==720);property_bits|=1;}
 else if(!strcmp(n,"IOSurfaceHeight")){assert(v==1480);property_bits|=2;}
 else if(!strcmp(n,"IOSurfaceBytesPerRow")){assert(v==2880);property_bits|=4;}
 else{assert(!strcmp(n,"IOSurfaceAllocSize")&&v==4262400);property_bits|=8;}}
static CFMutableDictionaryRef properties(void)''')
stub=stub.replace('assert(d==(void*)1&&nextid<8)','assert(d==(void*)1&&nextid<8&&property_bits==15)')
start=stub.index('static struct{Surface(*IOSurfaceCreate)');end=stub.index('static void lock_surface',start)
stub=stub[:start]+r'''static size_t width(Surface s){assert(s);return 720;}static size_t height(Surface s){assert(s);return 1480;}
static size_t row(Surface s){assert(s);return 2880;}static unsigned format(Surface s){assert(s);return 0x42475241;}
static size_t allocated(Surface s){assert(s);return 4262400;}static void*address(Surface s){assert(s&&s->locked);return s->p;}
static struct{Surface(*IOSurfaceCreate)(CFMutableDictionaryRef);unsigned(*IOSurfaceGetID)(Surface);Surface(*IOSurfaceLookup)(unsigned);
 size_t(*IOSurfaceGetWidth)(Surface),(*IOSurfaceGetHeight)(Surface),(*IOSurfaceGetBytesPerRow)(Surface);unsigned(*IOSurfaceGetPixelFormat)(Surface);
 size_t(*IOSurfaceGetAllocSize)(Surface);void*(*IOSurfaceGetBaseAddress)(Surface);}api={create,getid,lookup,width,height,row,format,allocated,address};
'''+stub[end:]
start=stub.index('static int layer(');end=stub.index('static int end(',start)
stub=stub[:start]+r'''static int layer(void*p,unsigned n,Surface s,FBRect a,FBRect b,unsigned flags){(void)p;
 assert(!n&&!flags&&live==1&&!s->locked&&a.x==0&&a.y==0&&a.width==720&&a.height==1480&&b.x==0&&b.y==0&&b.width==720&&b.height==1480);
 chosen=s;return 0;}
'''+stub[end:]
stub=stub.replace('static struct{int(*open)',r'''static int size_display(void*p,FBSize*s){assert(p);s->width=720;s->height=1480;return 0;}
static struct{int(*open)''')
stub=stub.replace('unsigned(*type_id)(void);int(*begin)','unsigned(*type_id)(void);int(*size)(void*,FBSize*);int(*begin)').replace('fb={open_display,typeid_display,begin','fb={open_display,typeid_display,size_display,begin')
stub=stub.replace('maxlive==2&&sessions==2&&completed==32','maxlive==1&&sessions==1&&completed==2').replace('m46_baseline_main','m47_baseline_main').replace('return 68;','return 69;')
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m47-baseline.c').write_text(stub);exe=d/'test'
 subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=undefined','-I'+str(d),str(r/'tools/surface-fullpanel.c'),'-o',str(exe)],check=True)
 good=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
 assert good.returncode==70,(good.returncode,good.stderr)
 assert good.stdout.count('M48 FRAME PASS')==2 and 'M48 PASS:' in good.stdout
 env=os.environ.copy();env['M48_TEST_CORRUPT_SOURCE']='1'
 bad=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=15)
 assert bad.returncode==254 and 'm48_source_changed' in bad.stderr,(bad.returncode,bad.stderr)
 print('M48 actual user code: full geometry/property requests, two submissions, per-frame hash, CF cleanup and corrupt-source rejection PASS. Framework mocked; no device claim.')
