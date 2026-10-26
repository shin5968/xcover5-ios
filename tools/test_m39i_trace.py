"""Compile the actual patch payload and test MAC dispatch with tracing enabled.

Optional argument: patched XNU tree from CI. Tests the applied function, not a
second handwritten dispatch implementation. Never executes target Apple code.
"""
from pathlib import Path
import subprocess,sys,tempfile
repo=Path(__file__).resolve().parents[1]
patch=(repo/'xnu/patches/0060-xcover5-preferences-request-trace.patch').read_text()
head=patch.split('+++ b/security/xcover5_prefs_trace.h\n',1)[1]
header=''.join(line[1:] for line in head.splitlines(True) if line.startswith('+'))
assert header.startswith('/* Diagnostic') and header.endswith('#endif\n')
prefix='''
#define XC_PREFS_TRACE_HOST 1
#include <pthread.h>
#define os_atomic_inc_orig(p,o) __atomic_fetch_add((p),1,__ATOMIC_RELAXED)
#define os_atomic_store(p,v,o) __atomic_store_n((p),(v),__ATOMIC_RELEASE)
#define os_atomic_load(p,o) __atomic_load_n((p),__ATOMIC_ACQUIRE)
static unsigned proc_getuid(proc_t p){return (unsigned)p->uid;}
static int proc_getpid(proc_t p){return proc_pid(p);}
#include "prefs-trace.h"
static void *trace_worker(void *p){
 for(unsigned i=0;i<100;i++)xcover5_prefs_trace_record(p,1,NULL,381,103);
 return NULL;
}
'''
fixture=(repo/'tools/test_m39_policy.c').read_text()
start=fixture.index('int\n__mac_syscall(');end=fixture.index('\n}\n',start)+3
func=fixture[start:end]
func=func.replace('\tif (error) {\n\t\treturn error;\n\t}\n\tAUDIT_ARG',
 '\tif (error) {\n\t\txcover5_prefs_trace_record(p,0,"<copy-policy>",uap->call,error);\n\t\treturn error;\n\t}\n\tAUDIT_ARG',1)
func=func.replace('error = mac_proc_check_mac_syscall(p, target, uap->call);\n\tif (error) {\n\t\treturn error;',
 'error = mac_proc_check_mac_syscall(p, target, uap->call);\n\tif (error) {\n\t\tgoto done;',1)
func=func.replace('done:\n\treturn error;','done:\n\txcover5_prefs_trace_record(p,0,target,uap->call,error);\n\tif (uap->call == 2 && strcmp(target,"Sandbox") == 0) xcover5_prefs_trace_query(p,uap->arg,error);\n\treturn error;')
has_container=(repo/'xnu/patches/0061-xcover5-hackios-container-query.patch').exists()
if has_container:
 func=func.replace('        error = xcover5_bootstrap_check(p, uap->arg);\n    }',
 '        error = xcover5_bootstrap_check(p, uap->arg);\n    } else if (uap->call == 4 && strcmp(target, "Sandbox") == 0) {\n        error = xcover5_prefs_container_path(p, uap->arg);\n    }')
 # The new handler has its own actual-header VM/ABI tests. Keep existing
 # dispatch/lock tests independent with a sentinel callback result.
 prefix+='static int container_calls; static int xcover5_prefs_container_path(proc_t p,user_addr_t a){(void)p;(void)a;container_calls++;return EINVAL;}\n'
if (repo/'xnu/patches/0063-xcover5-preferences-self-read.patch').exists():
 header=header.replace('shown++ < 32','shown++ < 64').replace('groups > 32 ? groups-32','groups > 64 ? groups-64')
 func=func.replace('        error = xcover5_bootstrap_check(p, uap->arg);','        error = xcover5_bootstrap_check(p, uap->arg);\n        if (error == ENOPOLICY) error = xcover5_preferences_access(p,uap->arg);')
 prefix+='static int xcover5_preferences_access(proc_t p,user_addr_t a){(void)p;(void)a;return ENOPOLICY;}\n'
if (repo/'xnu/patches/0064-xcover5-preferences-passthrough.patch').exists():
 func=func.replace('        error = xcover5_prefs_container_path(p, uap->arg);\n    }','        error = xcover5_prefs_container_path(p, uap->arg);\n    } else if (uap->call == 12 && strcmp(target, "Sandbox") == 0) {\n        error = xcover5_prefs_passthrough(p,uap->arg);\n    }')
 prefix+='static int passthrough_calls; static int xcover5_prefs_passthrough(proc_t p,user_addr_t a){(void)p;(void)a;passthrough_calls++;return EINVAL;}\n'
if len(sys.argv)>1:
 tree=Path(sys.argv[1]);source=(tree/'security/mac_base.c').read_text()
 pos=source.index('int\n__mac_syscall(');stop=source.index('\n}\n',pos)+3
 applied=source[pos:stop]
 # Remove only compile-time diagnostic guards for comparison with the host fixture.
 normalized=applied.replace('#if defined(XCOVER5)\n','').replace('#endif\n','')
 expected=func.replace('#if defined(XCOVER5)\n','').replace('#endif\n','')
 assert normalized==expected,'applied MAC dispatcher differs from host-tested implementation'
 assert (tree/'security/xcover5_prefs_trace.h').read_text()==header
 func=applied
 for name,marker in [('bsd/dev/arm/systemcalls.c','xcover5_prefs_trace_record(proc,1,NULL,code,error);'),
                     ('bsd/kern/kern_exit.c','xcover5_prefs_trace_dump(p);')]:
  text=(tree/name).read_text();assert text.count(marker)==1,(name,marker)
fixture=fixture[:start]+prefix+func+fixture[end:]
# Add scopes, publication and truncation assertions after the existing dispatch tests.
at=fixture.rfind('}')
fixture=fixture[:at]+'''
 caller.p_comm="cfprefsd";
 policy_result=EPERM;DISPATCH(EPERM);
 policy_result=EINVAL;DISPATCH(EINVAL);
 mac_policy_list.entries[1].mpc=NULL;args.call=3;DISPATCH(ENOPOLICY);
 precheck=EPERM;DISPATCH(EPERM);precheck=0;
 args.policy=0;DISPATCH(EFAULT);args.policy=(uintptr_t)"Sandbox";
 assert(xc_prefs_total==5);caller.p_comm="launchd";
 memset(xc_prefs_events,0,sizeof(xc_prefs_events));xc_prefs_total=0;
 child.p_comm="m39-probe";child.uid=501;
 xcover5_prefs_trace_record(&child,0,"Sandbox",2,103);assert(xc_prefs_total==0);
 child.uid=0;child.p_comm="other";
 xcover5_prefs_trace_record(&child,0,"Sandbox",2,103);assert(xc_prefs_total==0);
 child.p_comm="m39-probe";
 xcover5_prefs_trace_record(&child,1,NULL,5,0);
 xcover5_prefs_trace_record(&child,1,NULL,5,-1);assert(xc_prefs_total==0);
 xcover5_prefs_trace_record(&child,0,"Sandbox",2,0);
 assert(xc_prefs_total==1 && xc_prefs_events[0].ready && xc_prefs_events[0].error==0);
 for(unsigned i=1;i<133;i++)xcover5_prefs_trace_record(&child,1,NULL,381,103);
 assert(xc_prefs_total==133);
 for(unsigned i=0;i<128;i++)assert(xc_prefs_events[i].ready && xc_prefs_events[i].pid==7);
 xcover5_prefs_trace_dump(&child);
 memset(xc_prefs_events,0,sizeof(xc_prefs_events));xc_prefs_total=0;
 pthread_t workers[4];
 for(unsigned i=0;i<4;i++)assert(!pthread_create(&workers[i],NULL,trace_worker,&child));
 for(unsigned i=0;i<4;i++)assert(!pthread_join(workers[i],NULL));
 assert(xc_prefs_total==400);
 for(unsigned i=0;i<128;i++)assert(xc_prefs_events[i].ready && xc_prefs_events[i].code==381 && xc_prefs_events[i].error==103);
 memset(xc_prefs_events,0,sizeof(xc_prefs_events));xc_prefs_total=0;
 for(unsigned i=0;i<XC_PREFS_TRACE_CAP+5;i++)xcover5_prefs_trace_record(&child,1,NULL,381,103);
 assert(xc_prefs_total==XC_PREFS_TRACE_CAP+5);
 for(unsigned i=0;i<XC_PREFS_TRACE_CAP;i++)assert(xc_prefs_events[i].ready);
 xcover5_prefs_trace_dump(&child);

 memset(xc_prefs_queries,0,sizeof(xc_prefs_queries));xc_prefs_query_total=0;
 child.p_comm="m39-probe";child.uid=0;child.bits=1;
 uint64_t qa[7]={99,7,(uintptr_t)"mach-lookup",6,(uintptr_t)"com.apple.cfprefsd.daemon",0x40000000,7};
 uint64_t before[7];memcpy(before,qa,sizeof(qa));
 xcover5_prefs_trace_query(&child,(uintptr_t)qa,103);
 assert(xc_prefs_query_total==1&&xc_prefs_queries[0].ready&&xc_prefs_queries[0].error==103);
 assert(!strcmp(xc_prefs_queries[0].filter,"com.apple.cfprefsd.daemon"));
 assert(!memcmp(before,qa,sizeof(qa)));
 qa[3]=3;qa[4]=1;xcover5_prefs_trace_query(&child,(uintptr_t)qa,EPERM);
 assert(!strcmp(xc_prefs_queries[1].filter,"<not-string>"));
 fault=1;xcover5_prefs_trace_query(&child,(uintptr_t)qa,103);assert(xc_prefs_queries[2].arg_error==EFAULT);
 fault=2;xcover5_prefs_trace_query(&child,(uintptr_t)qa,103);assert(xc_prefs_queries[3].operation_error==EFAULT);fault=0;
 child.uid=501;xcover5_prefs_trace_query(&child,0,103);assert(xc_prefs_query_total==4);child.uid=0;
 child.bits=0;xcover5_prefs_trace_query(&child,0,103);assert(xc_prefs_query_total==4);child.bits=1;
 child.p_comm="other";xcover5_prefs_trace_query(&child,0,103);assert(xc_prefs_query_total==4);child.p_comm="m39-probe";
 for(unsigned i=0;i<20;i++)xcover5_prefs_trace_query(&child,0,103);
 assert(xc_prefs_query_total==24);
 for(unsigned i=0;i<XC_PREFS_QUERY_CAP;i++)assert(xc_prefs_queries[i].ready);
 args.call=12;mac_policy_list.entries[0].mpc=&policy;
 int old_passthrough=passthrough_calls;
 policy_result=EPERM;DISPATCH(EPERM);policy_result=ENOPOLICY;DISPATCH(ENOPOLICY);policy_result=0;DISPATCH(0);
 assert(passthrough_calls==old_passthrough);mac_policy_list.entries[0].mpc=NULL;
 puts("M39K query ABI, scope, fault, no-write and bounded publication PASS (host only)");
 puts("M39I scope, real return preservation, publication, capacity and overflow PASS (host only)");
'''+fixture[at:]
if has_container:
 anchor=' assert(xc_prefs_total==5);caller.p_comm="launchd";'
 extra=' args.call=4;DISPATCH(EINVAL);assert(container_calls==1);args.call=12;DISPATCH(EINVAL);assert(passthrough_calls==1);args.call=3;\n'
 assert anchor in fixture
 fixture=fixture.replace(anchor,extra+' assert(xc_prefs_total==7);caller.p_comm="launchd";')
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'prefs-trace.h').write_text(header);(d/'test.c').write_text(fixture)
 subprocess.run(['cc','-pthread','-Wno-format','-Wno-unused-parameter',str(d/'test.c'),'-o',str(d/'test')],check=True)
 p=subprocess.run([str(d/'test')],capture_output=True,text=True,check=True)
 assert 'total=133 stored=133 overflow=0 inflight=0' in p.stdout
 assert 'call=381 rc=103 count=132' in p.stdout
 assert 'total=517 stored=512 overflow=5 inflight=0' in p.stdout
 print(p.stdout)
