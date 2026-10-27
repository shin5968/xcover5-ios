"""Compile the actual daemon domain-read fallback; no target Apple execution."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0072-xcover5-cfprefs-remote-read.patch').read_text()
h=''.join(l[1:] for l in p.split('+++ b/security/xcover5_prefs_remote_read.h\n',1)[1].splitlines(True) if l.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_remote_read.h').read_text()==h
 assert (t/'security/mac_base.c').read_text().count('if (error == ENOPOLICY) error = xcover5_preferences_remote_read(p,uap->arg);')==1
f=(r/'tools/test_m39_policy.c').read_text()
f=f.replace('int main(void){','static unsigned proc_getuid(proc_t p){return (unsigned)p->uid;}\n'+h+'\nint main(void){',1)
at=f.rfind('}')
f=f[:at]+r'''
 caller=(struct process){1,0,1,0,1,"launchd"};
 server=(struct process){6,1,6,0,1,"m39-probe"};
 child=(struct process){7,6,7,0,1,"m39-probe"};
 struct process daemon={10,1,10,0,1,"cfprefsd"};
 uint64_t decision=99,q[7]={(uintptr_t)&decision,6,(uintptr_t)"user-preference-read",28,(uintptr_t)"org.xcover5.m39",0x40000011,6},saved[7];
 memcpy(saved,q,sizeof(q));
 #define READ_CHECK(actor,want) do {decision=99;assert(xcover5_preferences_remote_read((actor),(uintptr_t)q)==(want));assert(refs==0&&creds==0);assert(decision==((want)==0?0:99));}while(0)
 READ_CHECK(&server,ENOPOLICY);READ_CHECK(&daemon,0);assert(!memcmp(saved,q,sizeof(q)));
 READ_CHECK(&daemon,0);assert(!memcmp(saved,q,sizeof(q)));
 q[4]=(uintptr_t)"org.xcover5.m390";READ_CHECK(&daemon,ENOPOLICY);
 q[4]=(uintptr_t)"org.other.app";READ_CHECK(&daemon,ENOPOLICY);
 q[4]=(uintptr_t)"/var/root/Library/Preferences/org.xcover5.m39.plist";READ_CHECK(&daemon,ENOPOLICY);
 q[4]=saved[4];
 q[2]=(uintptr_t)"file-read-data";READ_CHECK(&daemon,ENOPOLICY);
 q[2]=(uintptr_t)"user-preference-write";READ_CHECK(&daemon,ENOPOLICY);q[2]=saved[2];
 for(unsigned i=3;i<=6;i++){
  if(i==4)continue;
  uint64_t v=q[i];q[i]^=1;READ_CHECK(&daemon,ENOPOLICY);q[i]=v;
 }
 q[1]=0;READ_CHECK(&daemon,ENOPOLICY);q[1]=UINT64_MAX;READ_CHECK(&daemon,ENOPOLICY);
 q[1]=8;READ_CHECK(&daemon,ESRCH);q[1]=saved[1];
 q[6]=UINT64_C(0x100000006);READ_CHECK(&daemon,ENOPOLICY);q[6]=saved[6];
 server.uid=501;READ_CHECK(&daemon,ENOPOLICY);server.uid=0;
 server.bits=0;READ_CHECK(&daemon,ENOPOLICY);server.bits=1;
 server.p_comm="other";READ_CHECK(&daemon,ENOPOLICY);server.p_comm="m39-probe";
 daemon.p_comm="other";READ_CHECK(&daemon,ENOPOLICY);daemon.p_comm="cfprefsd";
 daemon.uid=501;READ_CHECK(&daemon,ENOPOLICY);daemon.uid=0;
 daemon.bits=0;READ_CHECK(&daemon,ENOPOLICY);daemon.bits=1;
 daemon.ppid=8;READ_CHECK(&daemon,ENOPOLICY);daemon.ppid=1;
 server.ppid=8;READ_CHECK(&daemon,ENOPOLICY);server.ppid=1;
 READ_CHECK(&child,ENOPOLICY); /* A client cannot name another live client. */
 q[1]=7;q[6]=7;READ_CHECK(&daemon,0);
 child.uid=501;READ_CHECK(&daemon,ENOPOLICY);child.uid=0;
 child.bits=0;READ_CHECK(&daemon,ENOPOLICY);child.bits=1;
 server.uid=501;READ_CHECK(&daemon,ENOPOLICY);server.uid=0;
 server.bits=0;READ_CHECK(&daemon,ENOPOLICY);server.bits=1;
 server.p_comm="other";READ_CHECK(&daemon,ENOPOLICY);server.p_comm="m39-probe";
 server.ppid=8;READ_CHECK(&daemon,ENOPOLICY);server.ppid=1;
 memcpy(q,saved,sizeof(q));
 struct process impostor={1,0,1,0,1,"launchd"};initproc=&impostor;READ_CHECK(&daemon,ENOPOLICY);initproc=&caller;
 for(fault=1;fault<=3;fault++)READ_CHECK(&daemon,EFAULT);fault=0;
 q[0]=0;assert(xcover5_preferences_remote_read(&daemon,(uintptr_t)q)==EFAULT&&refs==0&&creds==0);q[0]=saved[0];
 q[2]=0;READ_CHECK(&daemon,EFAULT);q[2]=saved[2];
 q[4]=0;READ_CHECK(&daemon,EFAULT);q[4]=saved[4];
 char overlong[80];memset(overlong,'x',sizeof(overlong)-1);overlong[sizeof(overlong)-1]=0;
 q[4]=(uintptr_t)overlong;READ_CHECK(&daemon,ENAMETOOLONG);q[4]=saved[4];
 assert(!memcmp(saved,q,sizeof(q)));
 puts("M39V actual header: exact domain/operation/ABI, root actor and live PIDversion/ancestry, fresh-reader path, negative domains/actors/flags, copy faults and reference balance PASS (host only)");
'''+f[at:]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(f)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
