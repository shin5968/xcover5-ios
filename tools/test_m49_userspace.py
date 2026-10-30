# Actual M49 orchestration with framework mocked; no device claim.
from pathlib import Path
import subprocess,tempfile,os
r=Path(__file__).resolve().parents[1]
source=(r/'tools/test_m48_userspace.py').read_text().split('with tempfile.TemporaryDirectory()')[0]
scope={'__file__':str(r/'tools/test_m48_userspace.py')}
exec(compile(source,'m48-mock-builder','exec'),scope)
stub=scope['stub'].replace('d->done==2&&d->issued==2','d->done==16&&d->issued==16').replace('M48_TEST_CORRUPT_SOURCE','M49_TEST_CORRUPT_SOURCE')
stub=stub.replace('maxlive==1&&sessions==1&&completed==2','maxlive==2&&sessions==1&&completed==16').replace('m47_baseline_main','m48_baseline_main').replace('return 69;','return 70;')
stub=stub.replace('static void CFRelease(', 'static uint64_t stats[7];\nstatic void CFRelease(')
stub=stub.replace('sessions++;free(d);','sessions++;stats[0]++;stats[1]=0;stats[2]=(unsigned)getpid();stats[3]=14;stats[4]=1;stats[5]=getenv("M49_TEST_BAD_RESTORE")?1:0;stats[6]=16;free(d);')
a=stub.index('static int begin(');b=stub.index('static int layer(',a)
stub=stub[:a]+'''static int begin(void*p,unsigned*out){struct Display*d=p;if(d->issued>=16)return 1;assert(d->issued==d->done);*out=++d->issued;return 0;}
'''+stub[b:]
stub=stub.replace('live==1','live==2').replace(' chosen=s;return 0;}',' assert(!lastslot||lastslot!=s->id);lastslot=s->id;chosen=s;return 0;}')
stub=stub.replace('d->done=d->issued;completed++;','d->done=d->issued;completed++;if(d->done>=3)stats[1]=1;')
a=stub.index('static int wait_frame(');b=stub.index('static int size_display(',a)
stub=stub[:a]+'''static int wait_frame(void*p,unsigned id,unsigned flags){struct Display*d=p;assert(!flags);return getenv("M49_TEST_PREMATURE")?0:(id==d->done?0:1);}
'''+stub[b:]
a=stub.index('static struct{CFMutableDictionaryRef(*matching)');b=stub.index('static int open_display(',a)
stub=stub[:a]+'''static int open_control(mach_port_t s,mach_port_t t,unsigned k,mach_port_t*out){assert(s==1&&t==1&&!k);*out=77;return 0;}
static int close_control(mach_port_t c){assert(c==77);return 0;}
static int call_control(mach_port_t c,unsigned sel,const uint64_t*in,unsigned ni,const void*si,size_t ns,uint64_t*out,unsigned*no,void*so,size_t*nso){
assert(c==77&&sel==93&&!in&&!ni&&!si&&!ns&&out&&*no==7&&!so&&!nso);memcpy(out,stats,sizeof stats);return 0;}
static struct{CFMutableDictionaryRef(*matching)(const char*);mach_port_t(*service)(mach_port_t,CFMutableDictionaryRef);int(*release)(mach_port_t);
int(*open)(mach_port_t,mach_port_t,unsigned,mach_port_t*);int(*close)(mach_port_t);int(*call)(mach_port_t,unsigned,const uint64_t*,unsigned,const void*,size_t,uint64_t*,unsigned*,void*,size_t*);}io={matching,service,release_service,open_control,close_control,call_control};
'''+stub[b:]
full=(r/'tools/surface-fullpanel.c').read_text()
stub+='\n#define M48_BYTES (720U*1480U*4U)\n'+full[full.index('static uint64_t full_hash'):full.index('static int run_fullpanel')]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'m48-baseline.c').write_text(stub);exe=d/'test'
 subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(d),str(r/'tools/surface-persistent.c'),'-o',str(exe)],check=True)
 for fault,where in [(None,None),('M49_TEST_CORRUPT_SOURCE','m49_source_changed'),('M49_TEST_BAD_RESTORE','m49_close_restore'),('M49_TEST_PREMATURE','m49_premature_completion')]:
  env=os.environ.copy()
  if fault:env[fault]='1'
  p=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=15)
  assert p.returncode==(189 if fault else 71),(fault,p.returncode,p.stdout,p.stderr)
  if fault:assert where in p.stderr and 'M49 PASS:' not in p.stdout
  else:assert 'M49 PASS:16 full frames/14 persistent copies;' in p.stdout
 print('M49 actual user code:16 full submissions/two alternating surfaces, premature wait rejection, hold state, close-generation/restore and source integrity gates PASS; framework mocked')
