"""Actual M39M header: ABI, vnode lifetime, scope and failure preservation."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
p=(r/'xnu/patches/0064-xcover5-preferences-passthrough.patch').read_text()
h=''.join(x[1:] for x in p.split('+++ b/security/xcover5_prefs_passthrough.h\n',1)[1].splitlines(True) if x.startswith('+'))
if len(sys.argv)>1:
 t=Path(sys.argv[1]);assert (t/'security/xcover5_prefs_passthrough.h').read_text()==h
 assert 'error = xcover5_prefs_passthrough(p,uap->arg);' in (t/'security/mac_base.c').read_text()
prefix=r"""
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ENOPOLICY 103
#define MAXPATHLEN 1024
#define user_addr_t uintptr_t
struct proc {unsigned uid;int bits;const char *p_comm;};
typedef struct proc *proc_t;
struct fileproc {int unused;};struct vnode {int unused;};typedef struct vnode *vnode_t;
static struct fileproc file;static struct vnode node;
static int stage,files,vnodes,lookups,writes;
static const char *pathname="/var/root/Library/Preferences";
static unsigned proc_getuid(proc_t p){return p->uid;}
static int proc_is64bit_data(proc_t p){return p->bits;}
static int proc_pid(proc_t p){(void)p;return 6;}
static int copyin(user_addr_t a,void *b,size_t n){if(stage==1||!a)return EFAULT;memcpy(b,(void*)a,n);return 0;}
static int fp_getfvp(proc_t p,int fd,struct fileproc **fp,vnode_t *vp){(void)p;lookups++;if(stage==2||fd!=5)return EBADF;*fp=&file;*vp=&node;files++;return 0;}
static int fp_drop(proc_t p,int fd,struct fileproc *fp,int locked){(void)p;(void)fd;(void)locked;assert(fp==&file&&files==1);files--;return 0;}
static int vnode_getwithref(vnode_t vp){assert(vp==&node&&files==1);if(stage==3)return ENOENT;vnodes++;return 0;}
static int vn_getpath(vnode_t vp,char *b,int *n){assert(vp==&node&&vnodes==1&&files==0);if(stage==4)return ENAMETOOLONG;assert(strlen(pathname)+1<=(unsigned)*n);strcpy(b,pathname);*n=strlen(b)+1;return 0;}
static void vnode_put(vnode_t vp){assert(vp==&node&&vnodes==1);vnodes--;}
"""
test=r"""
int main(void){
 struct proc actor={0,1,"m39-probe"};uint64_t a[2]={5,0x102},saved[2];memcpy(saved,a,sizeof(a));
 assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);assert(!memcmp(a,saved,sizeof(a)));
 actor.p_comm="cfprefsd";assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);
 for(unsigned i=1;i<=4;i++){stage=i;int want[]={0,EFAULT,EBADF,ENOENT,ENAMETOOLONG};assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==want[i]);assert(!files&&!vnodes);}stage=0;
 const char *allowed[]={"/private/var/root/Library/Preferences","/var/root/Library/Preferences/org.xcover5.m39.plist","/private/var/root/Library/Preferences/org.xcover5.m39.plist"};
 for(unsigned i=0;i<3;i++){pathname=allowed[i];assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==0);assert(!files&&!vnodes);}
 const char *denied[]={"/etc/passwd","/var/root/Library/Preferences.evil","/var/root/Library/Preferences/com.apple.other.plist","/var/mobile/Library/Preferences"};
 for(unsigned i=0;i<4;i++){pathname=denied[i];assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);assert(!files&&!vnodes);}
 int count=lookups;actor.uid=501;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.uid=0;
 actor.bits=0;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.bits=1;
 actor.p_comm="other";assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);actor.p_comm="m39-probe";
 a[1]=0x103;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);a[1]=0x102;
 a[0]=UINT64_MAX;assert(xcover5_prefs_passthrough(&actor,(uintptr_t)a)==ENOPOLICY);assert(count==lookups);
 assert(!files&&!vnodes&&!writes);puts("M39M actual header: ABI/scope/path/copy/vnode errors, reference balance and no writes PASS (host only)");
}
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+h+test)
 subprocess.run(['cc','-std=c11','-Wno-format',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
