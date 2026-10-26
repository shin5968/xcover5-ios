"""Compile the actual M39L header; never execute target Apple binaries."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0063-xcover5-preferences-self-read.patch').read_text()
a=p.split('+++ b/security/xcover5_prefs_access.h\n',1)[1].split('--- ',1)[0]
h=''.join(x[1:] for x in a.splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_access.h').read_text()==h
 assert 'if (error == ENOPOLICY) error = xcover5_preferences_access(p,uap->arg);' in (t/'security/mac_base.c').read_text()
f=(r/'tools/test_m39_policy.c').read_text()
f=f.replace('int main(void){','static unsigned proc_getuid(proc_t p){return (unsigned)p->uid;}\n'+h+'\nint main(void){',1)
at=f.rfind('}')
f=f[:at]+r"""
 caller.p_comm="m39-probe";caller.uid=0;caller.bits=1;fault=0;
 uint64_t decision=99,q[7]={(uintptr_t)&decision,1,(uintptr_t)"user-preference-read",28,1,0x40000011,1};
 uint64_t saved[7];memcpy(saved,q,sizeof(q));
 assert(xcover5_preferences_access(&caller,(uintptr_t)q)==0&&decision==0);
 assert(!memcmp(saved,q,sizeof(q)));
 caller.p_comm="cfprefsd";decision=99;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==0&&decision==0);
 caller.p_comm="other";decision=99;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==ENOPOLICY&&decision==99);
 caller.p_comm="m39-probe";caller.uid=501;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==ENOPOLICY);caller.uid=0;
 caller.bits=0;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==ENOPOLICY);caller.bits=1;
 for(unsigned i=1;i<7;i++){
  if(i==2||i==4)continue;
  uint64_t v=q[i];q[i]^=1;decision=99;
  assert(xcover5_preferences_access(&caller,(uintptr_t)q)==ENOPOLICY&&decision==99);q[i]=v;
 }
 q[2]=(uintptr_t)"user-preference-write";assert(xcover5_preferences_access(&caller,(uintptr_t)q)==ENOPOLICY);q[2]=saved[2];
 fault=1;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==EFAULT);
 fault=2;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==EFAULT);
 fault=3;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==EFAULT);fault=0;
 q[0]=0;assert(xcover5_preferences_access(&caller,(uintptr_t)q)==EFAULT);
 assert(!refs&&!creds);
 puts("M39L actual-header self/UID/version/operation/ABI/copy errors and no argument mutation PASS (host only)");
"""+f[at:]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(f)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
