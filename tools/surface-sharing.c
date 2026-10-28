/* M43: real IOSurface only after unchanged M39/M40/M41 return63.
 * Dynamic symbols avoid entry-time framework initialization. Child exec receives
 * an ID and test iteration, never pixels, pointers or inherited mapping handles. */
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <limits.h>
#include <mach/mach.h>
extern int m41_baseline_main(int,char **);
typedef CFTypeRef Surface;
static struct {
    Surface (*IOSurfaceCreate)(CFDictionaryRef);
    Surface (*IOSurfaceLookup)(uint32_t);
    uint32_t (*IOSurfaceGetID)(Surface);
    void *(*IOSurfaceGetBaseAddress)(Surface);
    size_t (*IOSurfaceGetWidth)(Surface),(*IOSurfaceGetHeight)(Surface);
    size_t (*IOSurfaceGetBytesPerRow)(Surface),(*IOSurfaceGetAllocSize)(Surface);
    uint32_t (*IOSurfaceGetPixelFormat)(Surface),(*IOSurfaceGetSeed)(Surface);
    int (*IOSurfaceLock)(Surface,uint32_t,uint32_t *);
    int (*IOSurfaceUnlock)(Surface,uint32_t,uint32_t *);
} api;
static void fail(int stage,const char *where) {
    fprintf(stderr,"XCOVER5 M43 FAIL stage=%d where=%s errno=%d\n",stage,where,errno);
    _exit(stage);
}
static void load_api(void) {
    void *lib=dlopen("/System/Library/Frameworks/IOSurface.framework/IOSurface",RTLD_NOW|RTLD_LOCAL);
    if(!lib){fprintf(stderr,"M43 dlopen: %s\n",dlerror());fail(200,"IOSurface_dlopen");}
#define RESOLVE(name) do {void *p=dlsym(lib,#name); if(!p)fail(201,#name); \
    _Static_assert(sizeof(api.name)==sizeof(p),"Darwin function pointer ABI");memcpy(&api.name,&p,sizeof(p));}while(0)
    RESOLVE(IOSurfaceCreate);RESOLVE(IOSurfaceLookup);RESOLVE(IOSurfaceGetID);
    RESOLVE(IOSurfaceGetBaseAddress);RESOLVE(IOSurfaceGetWidth);RESOLVE(IOSurfaceGetHeight);
    RESOLVE(IOSurfaceGetBytesPerRow);RESOLVE(IOSurfaceGetAllocSize);RESOLVE(IOSurfaceGetPixelFormat);
    RESOLVE(IOSurfaceGetSeed);RESOLVE(IOSurfaceLock);RESOLVE(IOSurfaceUnlock);
#undef RESOLVE
}
static void number(CFMutableDictionaryRef d,CFStringRef key,int64_t v) {
    CFNumberRef n=CFNumberCreate(NULL,kCFNumberSInt64Type,&v);if(!n)fail(202,"number");
    CFDictionarySetValue(d,key,n);CFRelease(n);
}
static CFMutableDictionaryRef properties(void) {
    CFMutableDictionaryRef d=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
    if(!d)fail(202,"dictionary");
    number(d,CFSTR("IOSurfaceWidth"),64);number(d,CFSTR("IOSurfaceHeight"),32);
    number(d,CFSTR("IOSurfaceBytesPerElement"),4);number(d,CFSTR("IOSurfaceBytesPerRow"),256);
    number(d,CFSTR("IOSurfacePixelFormat"),0x42475241);number(d,CFSTR("IOSurfaceAllocSize"),8192);
    CFDictionarySetValue(d,CFSTR("IOSurfaceIsGlobal"),kCFBooleanTrue);
    return d;
}
static uint32_t pattern(unsigned round,unsigned phase,unsigned x,unsigned y) {
    return 0xff000000U|(((x*17+y*31+round*53+phase*71)&255U)<<16)|
        (((x*13+y*7+round*29+phase*43)&255U)<<8)|((x*3+y*19+round*11+phase*97)&255U);
}
static volatile uint32_t *base(Surface s) {
    size_t alloc=api.IOSurfaceGetAllocSize(s);
    if(api.IOSurfaceGetWidth(s)!=64 || api.IOSurfaceGetHeight(s)!=32 ||
        api.IOSurfaceGetBytesPerRow(s)!=256 || api.IOSurfaceGetPixelFormat(s)!=0x42475241 ||
        alloc<8192 || alloc>(8U<<20) || !api.IOSurfaceGetBaseAddress(s))fail(205,"surface_metadata_or_mapping");
    return (volatile uint32_t*)api.IOSurfaceGetBaseAddress(s);
}
static void pixels(Surface s,unsigned round,unsigned phase,int write_it) {
    volatile uint32_t *p=base(s);
    for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++) {
        uint32_t value=pattern(round,phase,x,y);
        if(write_it)p[y*64+x]=value;
        else if(p[y*64+x]!=value)fail(210,"pixel_mismatch");
    }
}
static void lock_surface(Surface s,uint32_t flags,int unlock_it) {
    uint32_t seed=0;
    int rc=unlock_it?api.IOSurfaceUnlock(s,flags,&seed):api.IOSurfaceLock(s,flags,&seed);
    if(rc){fprintf(stderr,"M43 lock/unlock rc=%x\n",(unsigned)rc);fail(206,"lock_or_unlock");}
}
static unsigned parse_unsigned(const char *s) {
    char *end;errno=0;unsigned long n=strtoul(s,&end,10);
    if(errno || !*s || *end || n>UINT32_MAX)fail(207,"reader_arguments");
    return (unsigned)n;
}
/* M46C: byte-sized progress channel survives exec; bounded parent snapshot.
 * No preferences or IOSurface results are replaced by diagnostic transport. */
static int reader_progress_fd=-1;
static void reader_progress(unsigned char phase) {
    if(reader_progress_fd>=0) {
        ssize_t n;do {n=write(reader_progress_fd,&phase,1);}while(n<0 && errno==EINTR);
    }
#ifdef M43_HOST_TEST
    const char *hold=getenv("M46C_TEST_HOLD_PHASE");
    if(hold && (unsigned)strtoul(hold,NULL,10)==phase) {
        /* Host-only fault isolates parent timeout from the child alarm race. */
        alarm(0);sleep(20);
    }
#endif
}
static void publish_reader_timeout(pid_t pid,uint32_t sid,unsigned round,const char *mode,
                                   unsigned phase,int status,unsigned flags) {
    fprintf(stderr,"M46C TIMEOUT child=%d sid=%u round=%u mode=%s phase=%u status=%x flags=%u\n",
        pid,sid,round,mode,phase,status,flags);
#ifndef M43_HOST_TEST
    void *lib=dlopen("/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit",RTLD_NOW|RTLD_LOCAL);
    CFMutableDictionaryRef (*matching)(const char *);mach_port_t (*service)(mach_port_t,CFDictionaryRef);
    int (*open_service)(mach_port_t,mach_port_t,uint32_t,mach_port_t *);
    int (*close_service)(mach_port_t);int (*release_service)(mach_port_t);
    int (*call)(mach_port_t,uint32_t,const uint64_t *,uint32_t,const void *,size_t,uint64_t *,uint32_t *,void *,size_t *);
    if(!lib){fputs("M46C diagnostic IOKit unavailable\n",stderr);return;}
#define DIAG_RESOLVE(member,name) do {void *symbol=dlsym(lib,name);if(!symbol){fputs("M46C diagnostic symbol missing\n",stderr);return;}memcpy(&member,&symbol,sizeof(symbol));}while(0)
    DIAG_RESOLVE(matching,"IOServiceMatching");DIAG_RESOLVE(service,"IOServiceGetMatchingService");
    DIAG_RESOLVE(open_service,"IOServiceOpen");DIAG_RESOLVE(close_service,"IOServiceClose");
    DIAG_RESOLVE(release_service,"IOObjectRelease");DIAG_RESOLVE(call,"IOConnectCallMethod");
#undef DIAG_RESOLVE
    mach_port_t object=service(0,matching("IOMobileFramebuffer")),connection=0;
    if(!object){fputs("M46C diagnostic service missing\n",stderr);return;}
    int rc=open_service(object,mach_task_self(),0,&connection);release_service(object);
    if(!rc){uint64_t in[7]={(uint32_t)pid,sid,round,!strcmp(mode,"live")?1:2,phase,(uint32_t)status,flags};
        uint32_t count=0;rc=call(connection,91,in,7,NULL,0,NULL,&count,NULL,NULL);close_service(connection);}
    fprintf(stderr,"M46C diagnostic publish rc=%x\n",rc);
#endif
}
static int reader(int argc,char **argv) {
    if(argc!=6)fail(207,"reader_argc");
    unsigned fd=parse_unsigned(argv[5]);if(fd>INT_MAX)fail(207,"progress_fd");
    reader_progress_fd=(int)fd;reader_progress(2);
    alarm(12);reader_progress(3);load_api();reader_progress(4);uint32_t sid=parse_unsigned(argv[2]);unsigned round=parse_unsigned(argv[4]);
    reader_progress(5);Surface s=api.IOSurfaceLookup(sid);reader_progress(6);
    if(!strcmp(argv[3],"gone")) {
        if(s){CFRelease(s);fail(219,"released_ID_still_live");}
        reader_progress(13);printf("XCOVER5 M43 GONE PASS round=%u id=%u\n",round,sid);return 66;
    }
    if(strcmp(argv[3],"live") || !s)fail(208,"fresh_lookup");
    if(api.IOSurfaceGetID(s)!=sid)fail(209,"lookup_ID");
    reader_progress(7);lock_surface(s,0,0);reader_progress(8);
    pixels(s,round,0,0);reader_progress(9);pixels(s,round,1,1);reader_progress(10);
    lock_surface(s,0,1);reader_progress(11);
    CFRelease(s);reader_progress(12);reader_progress(13);
    printf("XCOVER5 M43 READER PASS round=%u id=%u read_A_write_B\n",round,sid);
    return 65;
}
static void child(const char *self,uint32_t sid,unsigned round,const char *mode,int expected) {
    char id_text[16],round_text[16];snprintf(id_text,sizeof(id_text),"%u",sid);snprintf(round_text,sizeof(round_text),"%u",round);
    int channel[2];if(pipe(channel))fail(243,"progress_pipe");
    int flags=fcntl(channel[0],F_GETFL);if(flags<0 || fcntl(channel[0],F_SETFL,flags|O_NONBLOCK)<0)fail(243,"progress_nonblock");
    char fd_text[16];snprintf(fd_text,sizeof(fd_text),"%d",channel[1]);
    pid_t pid=fork();if(pid<0)fail(212,"fork");
    if(pid==0){close(channel[0]);reader_progress_fd=channel[1];reader_progress(1);
        execl(self,self,"--m43-reader",id_text,mode,round_text,fd_text,(char*)NULL);_exit(213);}
    close(channel[1]);unsigned phase=0,diag_flags=1;
    int status=0;
    for(unsigned i=0;i<200;i++) {
        unsigned char progress[32];ssize_t n=read(channel[0],progress,sizeof(progress));
        if(n>0)for(ssize_t at=0;at<n;at++){if(progress[at]>=1 && progress[at]<=13 && progress[at]>=phase)phase=progress[at];else diag_flags|=4;}
        else if(!n)diag_flags|=2;
        else if(errno!=EAGAIN && errno!=EINTR)diag_flags|=4;
        pid_t got=waitpid(pid,&status,WNOHANG);
        if(got==pid) {
            close(channel[0]);
            if(!WIFEXITED(status) || WEXITSTATUS(status)!=expected) {
                fprintf(stderr,"M43 reader mode=%s native_status=%x expected=%d\n",mode,status,expected);fail(215,"reader_result");
            }
            return;
        }
        if(got<0 && errno!=EINTR)fail(214,"waitpid");
        usleep(50000);
    }
    /* Drain pending one-byte phases before terminating the timed-out reader. */
    unsigned char tail[32];ssize_t n=read(channel[0],tail,sizeof(tail));
    if(n>0)for(ssize_t at=0;at<n;at++){if(tail[at]>=1 && tail[at]<=13 && tail[at]>=phase)phase=tail[at];else diag_flags|=4;}
    kill(pid,SIGKILL);while(waitpid(pid,&status,0)<0 && errno==EINTR){}
    close(channel[0]);
    publish_reader_timeout(pid,sid,round,mode,phase,status,diag_flags);
    fail(216,"reader_timeout");
}
static int run_surface(const char *self) {
    alarm(30);puts("XCOVER5 M43 BEGIN: loading IOSurface after M39+M40+M41 PASS");load_api();
    if(api.IOSurfaceLookup(0)!=NULL)fail(203,"invalid_ID_zero");
#ifndef M43_HOST_TEST
    /* These check the port's explicitly bounded subset, not the host driver's limits. */
    for(unsigned which=0;which<4;which++) {
        CFMutableDictionaryRef d=properties();
        if(which==0)number(d,CFSTR("IOSurfaceWidth"),0);
        if(which==1)number(d,CFSTR("IOSurfaceBytesPerRow"),7);
        if(which==2)number(d,CFSTR("IOSurfaceWidth"),INT64_MAX);
        if(which==3)number(d,CFSTR("IOSurfaceAllocSize"),9U<<20);
        Surface bad=api.IOSurfaceCreate(d);CFRelease(d);
        if(bad){CFRelease(bad);fail(204,"invalid_shape_accepted");}
    }
    puts("XCOVER5 M43 BOUNDS PASS: zero/short_row/huge_integer/oversize rejected");
#endif
    for(unsigned round=0;round<2;round++) {
        CFMutableDictionaryRef d=properties();Surface s=api.IOSurfaceCreate(d);CFRelease(d);
        if(!s)fail(211,"IOSurfaceCreate");
        uint32_t sid=api.IOSurfaceGetID(s);if(!sid)fail(209,"created_ID");
        lock_surface(s,0,0);volatile uint32_t *p=base(s);
        for(size_t i=0;i<api.IOSurfaceGetAllocSize(s)/4;i++)if(p[i])fail(217,"new_buffer_not_zero");
        pixels(s,round,0,1);
#ifdef M43_HOST_TEST
        if(getenv("M43_TEST_CORRUPT"))p[100]^=1;
#endif
        uint32_t before=api.IOSurfaceGetSeed(s);lock_surface(s,0,1);
        child(self,sid,round,"live",65);
        lock_surface(s,1,0);pixels(s,round,1,0);lock_surface(s,1,1);
        if(api.IOSurfaceGetSeed(s)==before)fail(218,"seed_not_changed");
        CFRelease(s);child(self,sid,round,"gone",66);
        printf("XCOVER5 M43 ROUND PASS round=%u fresh_exec/read_write/release\n",round);
    }
    puts("XCOVER5 M43 PASS: M39+M40+M41 + IOSurface two fresh exec readers + shared pixels + release");
    return 64;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
    if(argc>1 && !strcmp(argv[1],"--m43-reader"))return reader(argc,argv);
    int result=m41_baseline_main(argc,argv);
    if(argc!=1 || result!=63)return result;
    return run_surface(argv[0]);
}
