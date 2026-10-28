"""Execute actual M47 orchestration with bounded fake framework, plus source corruption fault."""
from pathlib import Path
import subprocess,tempfile,os
r=Path(__file__).resolve().parents[1]
stub=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
typedef unsigned mach_port_t;typedef const void *CFTypeRef;typedef void *CFMutableDictionaryRef;
typedef struct Surf{unsigned kind,id,locked;uint32_t p[2048];}*Surface;
typedef struct{double x,y,width,height;}FBRect;
static Surface table[8];static unsigned nextid=1,live,maxlive,sessions,completed,selected[2],lastslot;
struct Display{unsigned kind,issued,done;};static Surface chosen;
static void fail(int n,const char*w){fprintf(stderr,"M47 FAIL %d %s\n",n,w);_exit(n);}
static unsigned mach_task_self(void){return 1;}
static CFMutableDictionaryRef properties(void){return (void*)1;}
static unsigned CFGetTypeID(CFTypeRef p){return *(const unsigned*)p;}
static void CFRelease(CFTypeRef p){if(p==(void*)1)return;unsigned kind=CFGetTypeID(p);
 if(kind==1){Surface s=(Surface)p;assert(!s->locked);table[s->id]=NULL;live--;free(s);}
 else{struct Display*d=(struct Display*)p;assert(d->done==16&&d->issued==16);sessions++;free(d);}}
static Surface create(CFMutableDictionaryRef d){assert(d==(void*)1&&nextid<8);Surface s=calloc(1,sizeof(*s));s->kind=1;s->id=nextid++;table[s->id]=s;live++;if(live>maxlive)maxlive=live;return s;}
static unsigned getid(Surface s){return s->id;}static Surface lookup(unsigned id){return table[id];}
static struct{Surface(*IOSurfaceCreate)(CFMutableDictionaryRef);unsigned(*IOSurfaceGetID)(Surface);Surface(*IOSurfaceLookup)(unsigned);}api={create,getid,lookup};
static void lock_surface(Surface s,unsigned flags,unsigned unlock){(void)flags;assert(s);if(unlock){assert(s->locked);s->locked=0;}else{assert(!s->locked);s->locked=1;}}
static volatile uint32_t *base(Surface s){assert(s->locked);return s->p;}
static uint64_t hash_pixels(const uint32_t*p){uint64_t h=14695981039346656037ULL;const uint8_t*b=(const uint8_t*)p;for(unsigned i=0;i<8192;i++)h=(h^b[i])*1099511628211ULL;return h;}
static CFMutableDictionaryRef matching(const char*n){assert(!strcmp(n,"IOMobileFramebuffer"));return(void*)1;}
static mach_port_t service(mach_port_t p,CFMutableDictionaryRef d){assert(!p&&d==(void*)1);return 1;}
static int release_service(mach_port_t p){assert(p==1);return 0;}
static struct{CFMutableDictionaryRef(*matching)(const char*);mach_port_t(*service)(mach_port_t,CFMutableDictionaryRef);int(*release)(mach_port_t);}io={matching,service,release_service};
static int open_display(mach_port_t s,mach_port_t t,unsigned k,void**o){assert(s==1&&t==1&&!k&&!live);struct Display*d=calloc(1,sizeof(*d));d->kind=2;*o=d;lastslot=0;selected[0]=selected[1]=0;return 0;}
static unsigned typeid_display(void){return 2;}
static int begin(void*p,unsigned*out){struct Display*d=p;assert(d->done==d->issued&&d->issued<16);*out=++d->issued;return 0;}
static int layer(void*p,unsigned n,Surface s,FBRect a,FBRect b,unsigned flags){(void)p;assert(!n&&!flags&&live==2&&!s->locked&&a.width==64&&a.height==32&&b.x==232&&b.y==676&&b.width==256&&b.height==128);
 unsigned slot=s->id%2;assert(!lastslot||lastslot!=s->id);lastslot=s->id;selected[slot]++;chosen=s;return 0;}
static int end(void*p){struct Display*d=p;assert(chosen&&d->issued==d->done+1);d->done=d->issued;completed++;if(getenv("M47_TEST_CORRUPT_SOURCE"))chosen->p[0]^=1;return 0;}
static int wait_frame(void*p,unsigned id,unsigned flags){struct Display*d=p;assert(!flags&&id==d->done);if(id==16)assert(selected[0]==8&&selected[1]==8);return 0;}
static struct{int(*open)(mach_port_t,mach_port_t,unsigned,void**);unsigned(*type_id)(void);int(*begin)(void*,unsigned*);int(*layer)(void*,unsigned,Surface,FBRect,FBRect,unsigned);int(*end)(void*);int(*wait)(void*,unsigned,unsigned);}fb={open_display,typeid_display,begin,layer,end,wait_frame};
static void finish(void){assert(!live&&maxlive==2&&sessions==2&&completed==32);}
static int m46_baseline_main(int argc,char**argv){(void)argc;(void)argv;atexit(finish);return 68;}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m46-baseline.c').write_text(stub)
 exe=d/'test';subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(d),str(r/'tools/surface-sequence.c'),'-o',str(exe)],check=True)
 good=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
 assert good.returncode==69,(good.returncode,good.stderr)
 assert good.stdout.count('M47 SESSION PASS')==2 and 'M47 PASS:' in good.stdout
 env=os.environ.copy();env['M47_TEST_CORRUPT_SOURCE']='1'
 bad=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=10)
 assert bad.returncode==250 and 'm47_source_changed' in bad.stderr,(bad.returncode,bad.stderr)
 print('M47 actual orchestration:32 submissions, alternating buffers, two connection lifecycles, zero retained surfaces; source corruption rejected PASS. Framework mocked, not hardware evidence.')
