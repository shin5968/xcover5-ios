# Actual first-failure selector, protocol tracing and progress/EPIPE handling.
from pathlib import Path
import ast,subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
patch=(r/'xnu/patches/0084-xcover5-m50-transport-diagnostic.patch').read_text()
added=''.join(x[1:] for x in patch.splitlines(True) if x.startswith('+') and not x.startswith('+++'))
helper=added[added.index('static uint64_t gM50ADiag'):added.index('static void xcM50ADiagReport')]
handler=added[added.index('  if(selector==95)'):]
if len(sys.argv)>1:
 s=(Path(sys.argv[1])/'iokit/Kernel/arm/MiniIOSurface.cpp').read_text()
 assert helper in s and handler in s and '    xcM50ADiagReport();' in s
m=ast.parse((r/'tools/test_m46c_diag.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in m.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix=prefix.replace('xcReaderDiagReport','xcM50ADiagReport').replace('struct Args{','struct Args{const void*structureInput=nullptr;')
kt=r'''
return 3;}
int main(){uint64_t v[20]={3,60,0,20,4,21,0,0,0,0,0,0xfffffffeULL,0,0,0,0,0,0,0,0};
Args a;a.structureInput=v;a.structureInputSize=sizeof v;
assert(!call(95,&a)&&reports==1&&gM50ADiag[0]==6&&gM50ADiag[1]==3&&gM50ADiag[5]==4);
uint64_t kept[21];memcpy(kept,gM50ADiag,sizeof kept);v[0]=5;assert(call(95,&a)==2);assert(!memcmp(kept,gM50ADiag,sizeof kept));v[0]=3;
assert(call(95,nullptr)==2);a.structureInput=nullptr;assert(call(95,&a)==2);a.structureInput=v;
for(unsigned size:{0u,159u,161u}){a.structureInputSize=size;assert(call(95,&a)==2);}a.structureInputSize=sizeof v;
for(unsigned i=0;i<20;i++){uint64_t old=v[i];v[i]=~uint64_t(0);assert(!xcM50ADiagValid(v,sizeof v));v[i]=old;}
actor="other";assert(call(95,&a)==1);actor="m39-probe";process.uid=1;assert(call(95,&a)==1);process.uid=0;process.ppid=6;assert(call(95,&a)==1);process.ppid=1;
a.scalarInputCount=1;assert(call(95,&a)==2);a.scalarInputCount=0;a.scalarOutputCount=1;assert(call(95,&a)==2);a.scalarOutputCount=0;
a.structureInputDescriptor=(void*)1;assert(call(95,&a)==2);a.structureInputDescriptor=nullptr;
a.structureOutputDescriptor=(void*)1;assert(call(95,&a)==2);a.structureOutputDescriptor=nullptr;
a.structureOutputSize=1;assert(call(95,&a)==2);a.structureOutputSize=0;
assert(reports==1&&!memcmp(kept,gM50ADiag,sizeof kept));
uint8_t unaligned[161];memcpy(unaligned+1,v,sizeof v);assert(xcM50ADiagValid(unaligned+1,sizeof v));
v[15]=0xffffffffULL;v[16]=0xffffffffULL;assert(xcM50ADiagValid(v,sizeof v));
puts("M50A actual diagnostic selector: first failure retained, identity/shape/bounds rejection, unaligned safe copy, raw malformed packet retained PASS");}
'''
ipc=r'''
#include <assert.h>
#include <signal.h>
#include <fcntl.h>
#include <stdio.h>
#include "panel-death-protocol.h"
#include "panel-death-diagnostic.h"
int main(void){int p[2];assert(!pipe(p));struct m50_packet packet={0};
assert(m50_receive(p[0],&packet,5)==-1&&errno==ETIMEDOUT);assert(m50_trace.poll_rc==0&&m50_trace.read_rc==-2&&!m50_trace.bytes);
struct m50_packet sent={M50_STARTED,21,0,0};assert(!m50_send(p[1],&sent));assert(!m50_receive(p[0],&packet,5));
assert(m50_trace.poll_rc==1&&m50_trace.read_rc==16&&m50_trace.bytes==16&&!m50_trace.read_errno);
close(p[1]);assert(m50_receive(p[0],&packet,5)==-1&&errno==EPROTO&&m50_trace.read_rc==0&&!m50_trace.bytes);close(p[0]);
assert(signal(SIGPIPE,SIG_IGN)!=SIG_ERR);assert(!pipe(p));close(p[0]);assert(m50_send(p[1],&sent)==-1&&errno==EPIPE);close(p[1]);
assert(!pipe(p));int flags=fcntl(p[0],F_GETFL);assert(flags>=0&&!fcntl(p[0],F_SETFL,flags|O_NONBLOCK));
errno=EACCES;m50a_event_write(p[1],4,0,0);assert(errno==EACCES);m50a_event_write(p[1],5,-1,EPIPE);
struct m50a_event last={0};unsigned diagnostic_flags=0;errno=ENOENT;m50a_event_drain(p[0],&last,&diagnostic_flags);
assert(errno==ENOENT&&last.phase==5&&last.result==-1&&last.error==EPIPE&&!diagnostic_flags);
m50a_event_write(p[1],17,0,0);m50a_event_drain(p[0],&last,&diagnostic_flags);assert(diagnostic_flags==4&&last.phase==5);
close(p[1]);m50a_event_drain(p[0],&last,&diagnostic_flags);assert(diagnostic_flags==6);close(p[0]);
puts("M50A actual protocol: timeout/EOF/full-packet traces, real SIGPIPE ignored->EPIPE remains failure, progress/errno/malformed/EOF flags PASS");}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)
 for name,text,compiler in [('selector',prefix+'\n#include <initializer_list>\n'+helper+'int call(unsigned selector,Args*a){\n'+handler+kt,'c++'),('transport',ipc,'cc')]:
  f=d/(name+('.cpp' if compiler=='c++' else '.c'));f.write_text(text)
  subprocess.run([compiler,'-std=c++17' if compiler=='c++' else '-std=c11','-D_DEFAULT_SOURCE','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined','-I'+str(r/'tools'),str(f),'-o',str(d/name)],check=True)
  subprocess.run([str(d/name)],check=True,timeout=10)
