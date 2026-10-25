/* Host boundary tests for the actual imported header; no Apple binary execution. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <assert.h>
#define XC_PREFS_CONTAINER_HOST 1
#define ENOPOLICY 103
#define ARG_MAX 262144
#define FALSE 0
#define KMA_DATA 1
#define KMA_ZERO 2
#define VM_KERN_MEMORY_BSD 1
#define KERN_SUCCESS 0
typedef uintptr_t user_addr_t,vm_offset_t,vm_map_address_t;
typedef size_t user_size_t,vm_size_t;
struct process {int pid,version,uid,bits;const char *p_comm;user_addr_t user_stack;size_t p_argslen;};
typedef struct process *proc_t,*task_t;
typedef void *vm_map_t,*vm_map_copy_t;
#define PROC_NULL NULL
#define TASK_NULL NULL
#define VM_MAP_NULL NULL
static vm_map_t kernel_map=(void*)1;
static struct process caller={6,21,0,1,"m39-probe",0,0},target={10,22,0,1,"cfprefsd",0,0};
static unsigned char stackbytes[16384];
static int refs,tasks,maps,allocs,copies,copyfault,allocfail,mapfail,infail,overfail,notask;
static int xc_prefs_actor(proc_t p){return p->uid==0&&(!strcmp(p->p_comm,"cfprefsd")||!strcmp(p->p_comm,"m39-probe"));}
static int proc_is64bit_data(proc_t p){return p->bits;}
static int proc_getpid(proc_t p){return p->pid;}
static int proc_pidversion(proc_t p){return p->version;}
static proc_t proc_find(int pid){if(pid!=target.pid)return NULL;refs++;return &target;}
static void proc_rele(proc_t p){assert(p==&target);refs--;}
static task_t proc_task(proc_t p){return notask?NULL:p;}
static void task_reference(task_t t){assert(t);tasks++;}
static void task_deallocate(task_t t){assert(t);tasks--;}
static vm_map_t get_task_map_reference(task_t t){assert(t);if(mapfail)return NULL;maps++;return t;}
static void vm_map_deallocate(vm_map_t m){assert(m);maps--;}
static size_t vm_map_page_mask(vm_map_t m){assert(m);return 16383;}
static size_t vm_map_round_page(size_t n,size_t mask){return (n+mask)&~mask;}
static int copyin(user_addr_t p,void *b,size_t n){if(!p||copyfault==1)return EFAULT;memcpy(b,(void*)p,n);return 0;}
static int copyout(const void *p,user_addr_t b,size_t n){if(!b||copyfault==2)return EFAULT;memcpy((void*)b,p,n);return 0;}
static int kmem_alloc(vm_map_t m,vm_offset_t *p,size_t n,int f,int k){(void)m;(void)f;(void)k;if(allocfail)return 1;*p=(uintptr_t)calloc(1,n);assert(*p);allocs++;return 0;}
static void kmem_free(vm_map_t m,vm_offset_t p,size_t n){(void)m;(void)n;free((void*)p);allocs--;}
static int vm_map_copyin(vm_map_t m,vm_map_address_t p,size_t n,int f,vm_map_copy_t *c){(void)m;(void)f;if(infail)return 1;*c=malloc(n);assert(*c);memcpy(*c,(void*)p,n);copies++;return 0;}
static int vm_map_copy_overwrite(vm_map_t m,vm_offset_t p,vm_map_copy_t c,size_t n,int f){(void)m;(void)f;if(overfail)return 1;memcpy((void*)p,c,n);free(c);copies--;return 0;}
static void vm_map_copy_discard(vm_map_copy_t c){free(c);copies--;}
#include "container.h"
static void env(const void *data,size_t n){assert(n<=sizeof(stackbytes));memset(stackbytes,0,sizeof(stackbytes));memcpy(stackbytes+sizeof(stackbytes)-n,data,n);target.user_stack=(uintptr_t)(stackbytes+sizeof(stackbytes));target.p_argslen=n;}
int main(void){
 char output[128];struct {int64_t pid;uint64_t version;user_addr_t buffer;size_t size;uint64_t check;} a={10,22,(uintptr_t)output,sizeof(output),1};
 #define CHECK(want) do {assert(xcover5_prefs_container_path(&caller,(uintptr_t)&a)==(want));assert(!refs&&!tasks&&!maps&&!allocs&&!copies);}while(0)
 const char plain[]="cfprefsd\0HOME=/var/root\0USER=root\0";
 env(plain,sizeof(plain));memset(output,'?',sizeof(output));CHECK(0);assert(output[0]=='?');
 const char contained[]="app\0CFFIXED_USER_HOME=/private/var/mobile/test-container\0HOME=/var/mobile\0";
 env(contained,sizeof(contained));CHECK(0);assert(!strcmp(output,"/private/var/mobile/test-container"));
 a.size=strlen(output);CHECK(ENAMETOOLONG);a.size=sizeof(output);
 copyfault=2;CHECK(EFAULT);copyfault=1;CHECK(EFAULT);copyfault=0;
 a.version++;CHECK(ESRCH);a.check=0;CHECK(0);a.check=1;a.version=22;
 a.pid=INT64_MAX;CHECK(ESRCH);a.pid=-1;CHECK(ESRCH);a.pid=11;CHECK(ESRCH);a.pid=10;
 caller.uid=501;CHECK(ENOPOLICY);caller.uid=0;caller.p_comm="other";CHECK(ENOPOLICY);caller.p_comm="m39-probe";
 caller.bits=0;CHECK(ENOPOLICY);caller.bits=1;
 allocfail=1;CHECK(ENOMEM);allocfail=0;mapfail=1;CHECK(0);mapfail=0;
 infail=1;CHECK(0);infail=0;overfail=1;CHECK(0);overfail=0;
 notask=1;CHECK(0);notask=0;target.p_argslen=0;CHECK(0);
 env(contained,sizeof(contained));target.p_argslen=ARG_MAX+1;CHECK(EINVAL);
 env(contained,sizeof(contained));target.user_stack=1;CHECK(EINVAL);
 const char unterminated[]="CFFIXED_USER_HOME=/no-nul";env(unterminated,sizeof(unterminated)-1);output[0]='?';CHECK(0);assert(output[0]=='?');
 caller.p_comm="cfprefsd";env(plain,sizeof(plain));CHECK(0);
 puts("M39J actual header: container/no-container, PID version, scopes, bounds, copy/allocation/VM faults and reference balance PASS (host only)");
}
