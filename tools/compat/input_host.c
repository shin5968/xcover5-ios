/* Owned driver contract harness; include the actual imported queue implementation. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#define XC72_HOST_TEST 1
#define __unused __attribute__((unused))
#define LCK_GRP_DECLARE(n,s) int n
#define LCK_MTX_DECLARE(n,g) int n
#define FREAD 1
#define IO_NDELAY 4
#define PZERO 0
#define PCATCH 1
#define DEVFS_CHAR 1
#define UID_ROOT 0
#define GID_WHEEL 0
typedef long user_ssize_t;
struct proc;
struct uio { char *data; long resid; size_t offset; bool input,fail; };
static long uio_resid(struct uio*u){return u->resid;}
static int locks,waits,nodes,major_fail,node_fail,removed;
static void lck_mtx_lock(int *p){(void)p;assert(!locks);locks++;}
static void lck_mtx_unlock(int *p){(void)p;assert(locks==1);locks--;}
static int msleep(void*a,int*b,int c,const char*d,void*e){(void)a;(void)b;(void)c;(void)d;(void)e;waits++;return EINTR;}
static void wakeup(void *p){(void)p;}
static uint64_t mach_absolute_time(void){static uint64_t t;return ++t;}
static void absolutetime_to_nanoseconds(uint64_t t,uint64_t*n){*n=t;}
static bool PE_parse_boot_argn(const char*n,void*p,size_t s){(void)n;(void)p;(void)s;return false;}
static int uiomove(char*p,int n,struct uio*u){assert(!locks&&u->resid>=n);if(u->fail)return EFAULT;if(u->input)memcpy(p,u->data+u->offset,n);else memcpy(u->data+u->offset,p,n);u->resid-=n;u->offset+=n;return 0;}
static int eno_ioctl(void){return ENOTSUP;}
#define eno_stop eno_ioctl
#define eno_reset eno_ioctl
#define eno_select eno_ioctl
#define eno_mmap eno_ioctl
#define eno_strat eno_ioctl
struct cdevsw { int(*d_open)(dev_t,int,int,struct proc*);int(*d_close)(dev_t,int,int,struct proc*);int(*d_read)(dev_t,struct uio*,int);int(*d_write)(dev_t,struct uio*,int);int(*d_ioctl)(void),(*d_stop)(void),(*d_reset)(void),(*d_select)(void),(*d_mmap)(void),(*d_strategy)(void);int d_type; };
static int cdevsw_add(int n,const struct cdevsw*s){(void)n;(void)s;return major_fail?-1:20;}
static void cdevsw_remove(int n,const struct cdevsw*s){(void)n;(void)s;removed++;}
static dev_t makedev(int a,int b){return (dev_t)(a*256+b);}
static void*devfs_make_node(dev_t d,int t,int u,int g,int mode,const char*name){(void)d;(void)t;assert(!u&&!g&&mode==0644);assert(!strcmp(name,"hakios-touch")||!strcmp(name,"redwood-touch"));nodes++;return node_fail?NULL:(void*)1;}
#include "input.c"
int main(void){
 _Static_assert(sizeof(struct hakios_touch)==24,"ABI");
 major_fail=1;hakios_input_init();assert(!nodes);major_fail=0;node_fail=1;hakios_input_init();assert(removed==1);node_fail=0;nodes=0;hakios_input_init();assert(nodes==2);
 assert(!touch_open(0,FREAD,0,NULL));assert(touch_open(0,FREAD,0,NULL)==EBUSY);assert(!touch_open(0,0,0,NULL));assert(!touch_close(0,0,0,NULL));assert(touch_reader);touch_close(0,FREAD,0,NULL);assert(!touch_reader);
 struct hakios_touch in={.type=HAKIOS_TOUCH_DOWN,.finger=3,.x=100,.y=999999},out={0};
 struct uio w={(char*)&in,23,0,true,false};assert(touch_write(0,&w,0)==EINVAL&&w.offset==0);
 w.resid=24;in.type=99;assert(touch_write(0,&w,0)==EINVAL&&touch_head==touch_tail);in.type=HAKIOS_TOUCH_DOWN;w.offset=0;w.resid=24;assert(!touch_write(0,&w,0));
 struct uio r={(char*)&out,24,0,false,true};assert(touch_read(0,&r,0)==EFAULT&&touch_tail-touch_head==1);r.fail=false;assert(!touch_read(0,&r,0));assert(out.type==in.type&&out.finger==3&&out.x==100&&out.y==65535&&out.time);
 r.resid=0;assert(!touch_read(0,&r,0));r.resid=23;assert(touch_read(0,&r,0)==EINVAL);r.resid=24;assert(touch_read(0,&r,IO_NDELAY)==EWOULDBLOCK);assert(touch_read(0,&r,0)==EINTR&&waits==1&&!locks);
 for(unsigned i=0;i<600;i++)hakios_touch_post(HAKIOS_TOUCH_MOVE,i,0,0);
 assert(touch_tail-touch_head==512);r.offset=0;r.resid=24;assert(!touch_read(0,&r,0)&&out.finger==88);
 touch_head=touch_tail=UINT32_MAX-2;for(unsigned i=0;i<5;i++)hakios_touch_post(HAKIOS_TOUCH_UP,i,0,0);assert(touch_tail-touch_head==5);
 for(unsigned i=0;i<5;i++){r.offset=0;r.resid=24;assert(!touch_read(0,&r,0)&&out.finger==i);}assert(touch_head==touch_tail&&!locks);
 puts("M72 actual input: registration/failures, one reader, 24-byte ABI, bounds, copy fault requeue, overflow, counter wrap, nonblocking/interrupted wait PASS");
}
