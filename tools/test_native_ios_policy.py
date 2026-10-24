#!/usr/bin/env python3
"""Compile the actual XNU iOS spawn policy for native/desktop configurations."""
from pathlib import Path
import subprocess,tempfile,sys
HEAD = '#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <assert.h>\n#define TRUE 1\n#define FALSE 0\n#define PLATFORM_IOS 2\n#define EACCES 13\n#define OS_REASON_EXEC 9\n#define EXEC_EXIT_REASON_WRONG_PLATFORM 14\ntypedef int boolean_t;\nstruct proc {char *p_name; int platform;};\nstruct _posix_spawnattr {int psa_platform;};\nstruct image_params {void *ip_px_sa;void *ip_vp; long ip_arch_offset;};\nstatic int unentitled_ios_sim_launch, ent;\nstatic int proc_platform(struct proc *p) {return p->platform;}\nstatic int IOVnodeHasEntitlement(void *v,long off,const char *key) {(void)v;(void)off;(void)key;return ent;}\nstatic int os_reason_create(int ns,int c) {assert(ns==9);return c;}\nstatic int policy(int platform,int attr,int dev_override,int entitlement) {\n struct proc proc={"test",platform};struct proc *p=&proc;\n struct _posix_spawnattr psa={attr};struct image_params img={attr<0?NULL:&psa,NULL,0};struct image_params *imgp=&img;\n int signature_failure_reason=0,error=0;unentitled_ios_sim_launch=dev_override;ent=entitlement;\n'
TAIL = '\n done: return error ? signature_failure_reason : 0;\n}\nint main(void) {\n int count=0;\n for(int platform=1;platform<=2;platform++)for(int attr=-1;attr<=3;attr++)for(int override=0;override<2;override++)for(int entitlement=0;entitlement<2;entitlement++) {\n  int expected=0;\n  if(XNU_TARGET_OS_OSX && platform==2) {\n   if(attr>0 && attr!=2)expected=14;\n   if(attr<=0) {\n#if !defined(ARM64_BOARD_CONFIG_SWEET)\n#if DEBUG || DEVELOPMENT\n    if(!override&&!entitlement)expected=14;\n#else\n    expected=14;\n#endif\n#endif\n   }\n  }\n  assert(policy(platform,attr,override,entitlement)==expected);count++;\n }\n printf("Actual policy matrix PASS %d cases\\n",count);\n}\n'
def extract(text):
 start=text.index('#if XNU_TARGET_OS_OSX\n\t/* Check for platform passed in spawn attr')
 end=text.index('#endif /* XNU_TARGET_OS_OSX */',start)+len('#endif /* XNU_TARGET_OS_OSX */')
 return text[start:end]
if __name__=='__main__':
 source=Path(sys.argv[1])/'bsd/kern/kern_exec.c'
 block=extract(source.read_text())
 assert 'Native iOS port: omitted simulator platform' in block
 configs=[('sweet-dev',['-DXNU_TARGET_OS_OSX=1','-DARM64_BOARD_CONFIG_SWEET','-DDEVELOPMENT=1']),('sweet-release',['-DXNU_TARGET_OS_OSX=1','-DARM64_BOARD_CONFIG_SWEET']),('desktop-dev',['-DXNU_TARGET_OS_OSX=1','-DDEVELOPMENT=1']),('desktop-release',['-DXNU_TARGET_OS_OSX=1']),('native-ios',['-DXNU_TARGET_OS_OSX=0'])]
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);c=root/'policy.c';c.write_text(HEAD+block+TAIL)
  for name,flags in configs:
   exe=root/name
   subprocess.run(['cc','-std=c11',*flags,str(c),'-o',str(exe)],check=True)
   r=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
   assert 'matrix PASS 40 cases' in r.stdout
   print(name,'actual XNU policy PASS40')
 print('200 policy cases passed; Mach-O loading, entitlements and hardware not simulated.')
