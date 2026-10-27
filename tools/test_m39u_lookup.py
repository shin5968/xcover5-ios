"""Compile the actual M39U header; do not execute any target Apple binary."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0071-xcover5-cfprefs-self-lookup.patch').read_text()
h=''.join(l[1:] for l in p.split('+++ b/security/xcover5_prefs_self_lookup.h\n',1)[1].splitlines(True) if l.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_self_lookup.h').read_text()==h
 assert (t/'security/mac_base.c').read_text().count('if (error == ENOPOLICY) error = xcover5_preferences_self_lookup(p,uap->arg);')==1
f=(r/'tools/test_m39_policy.c').read_text()
f=f.replace('int main(void){','static unsigned proc_getuid(proc_t p){return (unsigned)p->uid;}\n'+h+'\nint main(void){',1)
at=f.rfind('}')
f=f[:at]+r'''
 caller=(struct process){1,0,1,0,1,"launchd"};
 server=(struct process){6,1,6,0,1,"m39-probe"};
 child=(struct process){7,6,7,0,1,"m39-probe"};
 uint64_t decision=99,q[7]={(uintptr_t)&decision,6,(uintptr_t)"mach-lookup",6,(uintptr_t)"com.apple.cfprefsd.daemon",0x1,0},saved[7];
 memcpy(saved,q,sizeof(q));
 #define LOOKUP_CHECK(actor,want) do {decision=99;assert(xcover5_preferences_self_lookup((actor),(uintptr_t)q)==(want));assert(refs==0&&creds==0);assert(decision==((want)==0?0:99));}while(0)
 LOOKUP_CHECK(&server,0);assert(!memcmp(saved,q,sizeof(q)));
 q[4]=(uintptr_t)"com.apple.cfprefsd.daemon.system";LOOKUP_CHECK(&server,0);
 q[4]=(uintptr_t)"com.apple.cfprefsd.daemon.other";LOOKUP_CHECK(&server,ENOPOLICY);
 q[4]=(uintptr_t)"com.apple.logd";LOOKUP_CHECK(&server,ENOPOLICY);q[4]=saved[4];
 q[2]=(uintptr_t)"mach-cross-domain-lookup";LOOKUP_CHECK(&server,ENOPOLICY);q[2]=saved[2];
 q[2]=(uintptr_t)"user-preference-write";LOOKUP_CHECK(&server,ENOPOLICY);q[2]=saved[2];
 q[1]=7;LOOKUP_CHECK(&server,ENOPOLICY);LOOKUP_CHECK(&child,0);
 server.uid=501;LOOKUP_CHECK(&child,ENOPOLICY);server.uid=0;
 server.bits=0;LOOKUP_CHECK(&child,ENOPOLICY);server.bits=1;
 server.p_comm="other";LOOKUP_CHECK(&child,ENOPOLICY);server.p_comm="m39-probe";
 server.ppid=8;LOOKUP_CHECK(&child,ENOPOLICY);server.ppid=1;
 memcpy(q,saved,sizeof(q));
 for(unsigned i=1;i<=6;i++){if(i==2||i==4)continue;uint64_t v=q[i];q[i]^=1;LOOKUP_CHECK(&server,ENOPOLICY);q[i]=v;}
 q[1]=UINT64_C(0x100000006);LOOKUP_CHECK(&server,ENOPOLICY);q[1]=saved[1];
 server.uid=501;LOOKUP_CHECK(&server,ENOPOLICY);server.uid=0;
 server.bits=0;LOOKUP_CHECK(&server,ENOPOLICY);server.bits=1;
 server.p_comm="cfprefsd";LOOKUP_CHECK(&server,ENOPOLICY);server.p_comm="other";LOOKUP_CHECK(&server,ENOPOLICY);server.p_comm="m39-probe";
 server.ppid=8;LOOKUP_CHECK(&server,ENOPOLICY);server.ppid=1;
 struct process impostor={1,0,1,0,1,"launchd"};initproc=&impostor;LOOKUP_CHECK(&server,ENOPOLICY);initproc=&caller;
 for(fault=1;fault<=3;fault++)LOOKUP_CHECK(&server,EFAULT);fault=0;
 q[0]=0;assert(xcover5_preferences_self_lookup(&server,(uintptr_t)q)==EFAULT&&refs==0&&creds==0);q[0]=saved[0];
 q[2]=0;LOOKUP_CHECK(&server,EFAULT);q[2]=saved[2];
 q[4]=0;LOOKUP_CHECK(&server,EFAULT);q[4]=saved[4];
 char longname[80];memset(longname,'x',79);longname[79]=0;q[4]=(uintptr_t)longname;LOOKUP_CHECK(&server,ENAMETOOLONG);q[4]=saved[4];
 assert(!memcmp(saved,q,sizeof(q)));
 puts("M39U actual-header self-PID/no-token ABI, exact services/flags/filter, root64 init and fresh reader ancestry, copy failures and reference balance PASS (host only)");
'''+f[at:]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(f)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
