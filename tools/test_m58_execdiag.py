"""Actual exec permission body: read-only diagnostics preserve results/state/calls."""
from pathlib import Path
import hashlib,subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0088-xcover5-chrono-exec-stages.patch').read_text()
header=''.join(x[1:] for x in p.split('+++ b/bsd/kern/xcover5_exec_stage.h\n')[1].splitlines(True) if x.startswith('+'))
fixture=(r/'tools/m58-permissions.c').read_text();function=fixture[fixture.index('\nexec_check_permissions('):]
base=''.join(line for line in function.splitlines(True) if 'XC58_STAGE(' not in line and 'XC58_ATTRS(' not in line)
assert hashlib.sha256(base.encode()).hexdigest()=='54b08596022dcae7ed61881ae7fd516871d888d423cc547f0d4003c8b10b54b1','non-diagnostic permission code changed'
stages=['saved_path','namei','transition','permissions_begin','permissions_end','header_read','image_begin','image_end','activate_return','not_regular','getattr','no_execute_bits','zero_size','mac_exec','process_signature','thread_signature']
if len(sys.argv)>1:
 t=Path(sys.argv[1]);s=(t/'bsd/kern/kern_exec.c').read_text()
 assert (t/'bsd/kern/xcover5_exec_stage.h').read_text()==header
 a=s.index('\nexec_check_permissions(struct image_params *imgp)\n{');b=s.index('\n}\n',a)+3
 assert s[a:b]==function
 assert s.count('#include "xcover5_exec_stage.h"')==1
 for stage in stages:assert s.count('XC58_STAGE(imgp,"'+stage+'",')==1,stage
 assert s.count('XC58_STAGE(imgp,"vnode_authorize",')==2 and s.count('XC58_ATTRS(imgp);')==1
 a=s.index('\nexec_activate_image(struct image_params *imgp)\n{');b=s.index('\n}\n',a)+3
 assert s.index('XC58_STAGE(imgp,"activate_return",',a)<s.index('execargs_free(imgp);',a,b)
 if '--source-only' in sys.argv:
  print('M58 actual applied stage locations, logging before path release, exact permission body/no authorization changes PASS');raise SystemExit(0)
prefix=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <sys/stat.h>
#define CONFIG_MACF 1
#define EXECUTABLE_KEY "executable_path="
#define NCARGS 4096
#define PAGE_SIZE 4096
#define MNT_NOSUID 8
#define P_LTRACED 1
#define VSUID S_ISUID
#define VSGID S_ISGID
#define IMGPF_ALLOW_DATA_EXEC 4
#define IMGPF_DISABLE_ASLR 8
#define KAUTH_VNODE_EXECUTE 1
#define KAUTH_VNODE_READ_DATA 2
typedef uint64_t user_size_t;typedef unsigned kauth_action_t;
struct Proc{int pid;unsigned uid,p_lflag;};typedef struct Proc*proc_t;
struct Mount{uint64_t mnt_flag;int opaque;};struct vnode{struct Mount*v_mount;int regular;};
struct vnode_attr{unsigned va_uid,va_gid,va_mode;uint64_t va_data_size;};
struct image_params{struct vnode*ip_vp;struct vnode_attr*ip_vattr;proc_t ip_vfs_context;uint64_t ip_arch_offset,ip_arch_size;unsigned ip_flags;char*ip_strings,*ip_strendp;};
static struct Proc actor={17,501,0};static struct Mount mount;
static struct vnode node={&mount,1};static struct vnode_attr supplied;
static int attr_error,mac_error,auth_error;static char calls[16];static unsigned used,last_action,prints;
static int proc_getpid(proc_t p){return p->pid;}static proc_t vfs_context_proc(proc_t p){return p;}
static proc_t vfs_context_ucred(proc_t p){return p;}static unsigned kauth_cred_getuid(proc_t p){return p->uid;}
static void record(char c){assert(used<sizeof calls);calls[used++]=c;}
static int vnode_isreg(struct vnode*v){record('R');return v->regular;}
static struct Mount*vnode_mount(struct vnode*v){return v->v_mount;}
static int vfs_authopaque(struct Mount*m){return m->opaque;}
#define VATTR_INIT(p) memset(p,0,sizeof(*(p)))
#define VATTR_WANTED(p,f) ((void)0)
static int vnode_getattr(struct vnode*v,struct vnode_attr*a,proc_t c){assert(v==&node&&c==&actor);record('G');if(attr_error)return attr_error;*a=supplied;return 0;}
static int mac_vnode_check_exec(proc_t c,struct vnode*v,struct image_params*i){assert(c==&actor&&v==&node&&i);record('M');return mac_error;}
static int vnode_authorize(struct vnode*v,void*x,kauth_action_t a,proc_t c){assert(v==&node&&!x&&c==&actor);record('A');last_action=a;return auth_error;}
static int trace_printf(const char*,...) __attribute__((format(printf,1,2)));
static int trace_printf(const char*f,...){(void)f;prints++;return 0;}
#define printf trace_printf
'''
test=r'''
static char strings[256];
static void reset(unsigned which){
 actor.p_lflag=0;mount=(struct Mount){0,0};node.regular=1;supplied=(struct vnode_attr){0,0,0755,65184};attr_error=mac_error=auth_error=0;
 if(which==1)node.regular=0;if(which==2)attr_error=EIO;if(which==3)supplied.va_mode=0644;
 if(which==4)supplied.va_data_size=0;if(which==5)mac_error=EPERM;if(which==6)auth_error=EACCES;
 if(which==7)actor.p_lflag=P_LTRACED;if(which==8){mount.mnt_flag=MNT_NOSUID;supplied.va_mode|=VSUID|VSGID;}
 if(which==9){mount.opaque=1;supplied.va_mode=0644;}used=last_action=prints=0;memset(calls,0,sizeof calls);
}
int main(void){
 strcpy(strings,EXECUTABLE_KEY "/System/Library/PrivateFrameworks/ChronoCore.framework/Support/chronod");
 char unchanged[sizeof strings];memcpy(unchanged,strings,sizeof strings);
 for(unsigned which=0;which<10;which++){
  struct vnode_attr original={0},observed={0};
  struct image_params i={&node,&original,&actor,99,111,0x100|IMGPF_ALLOW_DATA_EXEC|IMGPF_DISABLE_ASLR,strings,strings+strlen(strings)+1};
  reset(which);int expected=original_permissions(&i);char expected_calls[16];memcpy(expected_calls,calls,sizeof calls);unsigned expected_used=used,expected_action=last_action;
  uint64_t offset=i.ip_arch_offset,size=i.ip_arch_size;unsigned flags=i.ip_flags;
  reset(which);i.ip_vattr=&observed;i.ip_arch_offset=99;i.ip_arch_size=111;i.ip_flags=0x100|IMGPF_ALLOW_DATA_EXEC|IMGPF_DISABLE_ASLR;
  int actual=exec_check_permissions(&i);assert(actual==expected&&used==expected_used&&last_action==expected_action&&!memcmp(calls,expected_calls,sizeof calls));
  assert(!memcmp(&original,&observed,sizeof original)&&i.ip_arch_offset==offset&&i.ip_arch_size==size&&i.ip_flags==flags);
  assert(!memcmp(strings,unchanged,sizeof strings));
#if defined(XCOVER5)
  assert(prints>0);
#else
  assert(!prints);
#endif
 }
#if defined(XCOVER5)
 struct vnode_attr a;struct image_params i={&node,&a,&actor,0,0,0,strings,strings+strlen(strings)+1};
 assert(xcover5_exec_stage_target(&i));assert(!xcover5_exec_stage_target(NULL));
 i.ip_strendp=strings+3;assert(!xcover5_exec_stage_target(&i));
 i.ip_strendp=(char*)((uintptr_t)strings+NCARGS+PAGE_SIZE+1);assert(!xcover5_exec_stage_target(&i));
 i.ip_strendp=(char*)((uintptr_t)strings-1);assert(!xcover5_exec_stage_target(&i));
 strcpy(strings,EXECUTABLE_KEY "/bin/chronod");i.ip_strendp=strings+strlen(strings)+1;assert(!xcover5_exec_stage_target(&i));
 strcpy(strings,EXECUTABLE_KEY "/System/Library/PrivateFrameworks/ChronoCore.framework/Support/chronodX");i.ip_strendp=strings+strlen(strings)+1;assert(!xcover5_exec_stage_target(&i));
 i.ip_strings=NULL;assert(!xcover5_exec_stage_target(&i));
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);source=prefix+header+'\nstatic int'+base.replace('exec_check_permissions(','original_permissions(',1)+'\n'+fixture+'\n'+test
 (d/'test.c').write_text(source)
 for flags in [['-DXCOVER5'],[]]:
  subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=undefined',*flags,str(d/'test.c'),'-o',str(d/'test')],check=True)
  subprocess.run([str(d/'test')],check=True)
print('M58 actual original/instrumented permission bodies: identical rc/state/policy calls under10 success/failure modes; exact bounded kernel path/read-only logging and non-XCover fallback PASS')
