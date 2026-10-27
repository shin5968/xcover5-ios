/* M39: real CoreFoundation APIs, separate exec reader, and RAM-root file check. */
#include <CoreFoundation/CoreFoundation.h>
#include "hackios_preferences.h"
#include <mach/mach.h>
/* bootstrap.h is private in the iPhone SDK; these are the libSystem MIG ABI
 * declarations used by the existing M36/M37 bootstrap lookup tests. */
extern mach_port_t bootstrap_port;
extern kern_return_t bootstrap_look_up(mach_port_t, const char *, mach_port_t *);
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <fcntl.h>
#include <pwd.h>
#include <objc/runtime.h>
#include <stdatomic.h>
#include <stddef.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "m39s-observer-api.h"
static CFStringRef app, key;
static int use_app_api=1;
static void preferences_set(CFPropertyListRef value) {
    if(use_app_api)hackios_preferences_set(key,value,app);
    else CFPreferencesSetValue(key,value,app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
}
static Boolean preferences_sync(void) {
    return use_app_api?hackios_preferences_sync(app):CFPreferencesSynchronize(app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
}
static CFPropertyListRef preferences_copy(void) {
    return use_app_api?hackios_preferences_copy(key,app):CFPreferencesCopyValue(key,app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
}
static void fail(int stage) { m39s_dump(); fprintf(stderr,"XCOVER5 M39 FAIL stage=%d errno=%d\n",stage,errno); _exit(stage); }
/* M39D: the error handler is a direct function, absent from the runtime method
 * list in the exact device cache. Observe the registered synchronize method.
 * Read atomic state before its original implementation consumes lastWriteFailed.
 * Missing instrumentation must not prevent the actual preferences test. */
typedef BOOL (*prefs_sync_imp)(id,SEL);
static prefs_sync_imp original_sync;
static ptrdiff_t state_offsets[4];
static _Atomic unsigned sync_logs;
static struct { _Atomic unsigned ready; unsigned flags[4]; int result; } source_events[8];
static void dump_source_observer(void) {
    int saved_errno=errno;unsigned total=atomic_load(&sync_logs),stored=total<8?total:8;
    printf("M39S SOURCE_CALLS total=%u stored=%u\n",total,stored);
    for(unsigned i=0;i<stored;i++)if(atomic_load_explicit(&source_events[i].ready,memory_order_acquire))
        printf("M39S SOURCE_SYNC seq=%u writeFailed=%u volatile=%u readonly=%u directMode=%u result=%d\n",i,source_events[i].flags[0],source_events[i].flags[1],source_events[i].flags[2],source_events[i].flags[3],source_events[i].result);
    errno=saved_errno;
}
static BOOL observe_preferences_sync(id self,SEL selector) {
    unsigned flags[4];
    for(unsigned i=0;i<4;i++)
        flags[i]=atomic_load_explicit((const _Atomic unsigned char *)((const char *)self+state_offsets[i]),memory_order_acquire);
    BOOL result=original_sync(self,selector);
    int saved_errno=errno;unsigned slot=atomic_fetch_add_explicit(&sync_logs,1,memory_order_relaxed);
    if(slot<8){
        memcpy(source_events[slot].flags,flags,sizeof(flags));source_events[slot].result=(int)result;
        atomic_store_explicit(&source_events[slot].ready,1,memory_order_release);
        fprintf(stderr,"M39D SOURCE_SYNC writeFailed=%u volatile=%u readonly=%u directMode=%u result=%d\n",flags[0],flags[1],flags[2],flags[3],(int)result);
    }
    errno=saved_errno;
    return result;
}
static void install_source_observer(void) {
    Class cls=objc_getClass("CFPrefsPlistSource");
    if(!cls){puts("M39D OBSERVER unavailable: class missing; test continues");return;}
    SEL selector=sel_registerName("synchronize");
    Method method=class_getInstanceMethod(cls,selector);
    if(!method){puts("M39D OBSERVER unavailable: synchronize missing; test continues");return;}
    const char *encoding=method_getTypeEncoding(method);
    printf("M39D OBSERVER encoding=%s arity=%u\n",encoding?encoding:"(null)",method_getNumberOfArguments(method));
    if(!encoding || strcmp(encoding,"B16@0:8") || method_getNumberOfArguments(method)!=2){puts("M39D OBSERVER unavailable: ABI mismatch; test continues");return;}
    const char *names[]={"_lastWriteFailed","_volatile","_readonly","_directMode"};
    for(unsigned i=0;i<4;i++){
        Ivar ivar=class_getInstanceVariable(cls,names[i]);
        const char *type=ivar?ivar_getTypeEncoding(ivar):NULL;
        if(!type || strcmp(type,"AB")){printf("M39D OBSERVER unavailable: ivar=%s type=%s; test continues\n",names[i],type?type:"(null)");return;}
        state_offsets[i]=ivar_getOffset(ivar);
        if(state_offsets[i]<0 || (size_t)state_offsets[i]>=class_getInstanceSize(cls)){puts("M39D OBSERVER unavailable: ivar offset; test continues");return;}
    }
    original_sync=(prefs_sync_imp)method_getImplementation(method);
    if(!original_sync){puts("M39D OBSERVER unavailable: implementation missing; test continues");return;}
    method_setImplementation(method,(IMP)observe_preferences_sync);
    puts("M39D OBSERVER ready: original synchronize return preserved");
}
/* Diagnostic operations use isolated temporary files; never overwrite preferences. */
static void filesystem_probe(const char *directory) {
    struct stat st; struct statfs fs;
    if (stat(directory,&st)) { fprintf(stderr,"M39A FS stat path=%s errno=%d\n",directory,errno); fail(151); }
    printf("M39A FS directory=%s uid=%u gid=%u mode=%o\n",directory,(unsigned)st.st_uid,(unsigned)st.st_gid,(unsigned)st.st_mode);
    if (statfs(directory,&fs)) { fprintf(stderr,"M39A FS statfs errno=%d\n",errno); fail(152); }
    printf("M39A FS flags=%lx free-blocks=%llu block-size=%u\n",(unsigned long)fs.f_flags,(unsigned long long)fs.f_bavail,(unsigned)fs.f_bsize);
    char temp[256],renamed[256];
    snprintf(temp,sizeof(temp),"%s/.m39a-%d.tmp",directory,getpid());
    snprintf(renamed,sizeof(renamed),"%s/.m39a-%d.done",directory,getpid());
    int fd=open(temp,O_RDWR|O_CREAT|O_EXCL,0600);
    if(fd<0){fprintf(stderr,"M39A FS open path=%s errno=%d\n",temp,errno);fail(153);}
    const char token[]="m39a-disk-check";
    if(write(fd,token,sizeof(token))!=(ssize_t)sizeof(token)){fprintf(stderr,"M39A FS write errno=%d\n",errno);fail(154);}
    if(fsync(fd)){fprintf(stderr,"M39A FS fsync errno=%d\n",errno);fail(155);}
    if(close(fd)){fprintf(stderr,"M39A FS close errno=%d\n",errno);fail(156);}
    if(rename(temp,renamed)){fprintf(stderr,"M39A FS rename errno=%d\n",errno);fail(157);}
    fd=open(renamed,O_RDONLY);char found[sizeof(token)];
    if(fd<0 || read(fd,found,sizeof(found))!=(ssize_t)sizeof(found) || memcmp(found,token,sizeof(token))){fprintf(stderr,"M39A FS readback errno=%d\n",errno);fail(158);}
    if(close(fd) || unlink(renamed)){fprintf(stderr,"M39A FS cleanup errno=%d\n",errno);fail(159);}
    printf("M39A FS PASS: create/write/fsync/rename/read/unlink %s\n",directory);
}
static int reader(void) {
    if (!preferences_sync()) fail(145);
    CFPropertyListRef value=preferences_copy();
    if (!value || CFGetTypeID(value)!=CFStringGetTypeID() || !CFEqual(value,CFSTR("m39-independent-read"))) fail(146);
    CFRelease(value);
    puts("XCOVER5 M39 READER PASS: fresh exec read expected preference");
    return 59;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0); setvbuf(stderr,NULL,_IONBF,0);
    alarm(60);
    app=CFSTR("org.xcover5.m39"); key=CFSTR("proof");
    use_app_api=!(argc==2 && (!strcmp(argv[1],"--legacy") || !strcmp(argv[1],"--read")));
    printf("M39H API=%s\n",use_app_api?"HackiOS application preferences":"legacy explicit user/host");
    if (argc==2 && (!strcmp(argv[1],"--read") || !strcmp(argv[1],"--read-app"))) return reader();
    if (getppid()!=1 || getuid()!=0) fail(140);
    printf("M39A ID uid=%u euid=%u gid=%u ppid=%d HOME=%s\n",(unsigned)getuid(),(unsigned)geteuid(),(unsigned)getgid(),getppid(),getenv("HOME")?getenv("HOME"):"(unset)");
    struct passwd *account=getpwuid(geteuid());
    printf("M39A ACCOUNT home=%s\n",account?account->pw_dir:"(lookup failed)");
    filesystem_probe("/var/root/Library/Preferences");
    filesystem_probe("/Library/Preferences");
    install_source_observer();
    int calibration=m39s_calibrate();
    printf("M39S OBSERVER calibration_value=%d interpose_hits=%u (zero means unavailable, not no error)\n",calibration,m39s_calibration_count());
    m39s_activate();
    puts("XCOVER5 M39 BEGIN: cfprefsd bootstrap lookup");
    mach_port_t port=MACH_PORT_NULL;
    kern_return_t kr=bootstrap_look_up(bootstrap_port,"com.apple.cfprefsd.daemon",&port);
    if (kr!=KERN_SUCCESS || !MACH_PORT_VALID(port)) { fprintf(stderr,"M39 bootstrap kr=%d\n",kr); fail(141); }
    mach_port_deallocate(mach_task_self(),port);
    puts("XCOVER5 M39: daemon port acquired, writing preference");
    preferences_set(CFSTR("m39-independent-read"));
    errno=0;
    Boolean synced=preferences_sync();
    dump_source_observer();
    printf("M39A SYNC returned=%d (errno is not a CFPreferences error code)\n",synced);
    if (!synced) fail(142);
    m39s_dump();
    struct stat st;
    if (stat("/var/root/Library/Preferences/org.xcover5.m39.plist",&st) || !S_ISREG(st.st_mode) || st.st_size<=0) fail(143);
    puts("XCOVER5 M39: preference synchronized to RAM filesystem, starting fresh reader");
    pid_t child=fork();
    if(child<0) fail(144);
    if(!child) { execl("/sbin/m39-probe","m39-probe",use_app_api?"--read-app":"--read",(char*)NULL); fail(147); }
    int status=0; pid_t got;
    do { got=waitpid(child,&status,0); } while(got<0 && errno==EINTR);
    if(got!=child || !WIFEXITED(status) || WEXITSTATUS(status)!=59) { fprintf(stderr,"M39 reader status=%x\n",status); fail(148); }
    preferences_set(NULL);
    if (!preferences_sync()) fail(149);
    CFPropertyListRef removed=preferences_copy();
    if(removed) { CFRelease(removed); fail(150); }
    puts("XCOVER5 M39 PASS: preferences write + sync + file + fresh exec read + cleanup (RAM only)");
    return 60;
}
