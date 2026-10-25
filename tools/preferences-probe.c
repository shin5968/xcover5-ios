/* M39: real CoreFoundation APIs, separate exec reader, and RAM-root file check. */
#include <CoreFoundation/CoreFoundation.h>
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
#include <dlfcn.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static CFStringRef app, key;
static void fail(int stage) { fprintf(stderr,"XCOVER5 M39 FAIL stage=%d errno=%d\n",stage,errno); _exit(stage); }
/* M39C: observe the actual reply in this test process, then forward unchanged.
 * No Apple file/code bytes or daemon policy are modified by this observer. */
typedef void (*prefs_error_imp)(id,SEL,void *,void *,void *,void *,long,int,void *);
static prefs_error_imp original_error;
static char *(*describe_xpc)(void *);
static unsigned reply_logs;
static void observe_preferences_error(id self,SEL selector,void *reply,void *message,
    void *keys,void *values,long count,int retry,void *continuation) {
    if (reply_logs++ < 8) {
        char *description=reply && describe_xpc ? describe_xpc(reply) : NULL;
        fprintf(stderr,"M39C ERROR_REPLY count=%ld retry=%d reply=%.1800s\n",count,retry,description?description:"(unavailable)");
        free(description);
    }
    original_error(self,selector,reply,message,keys,values,count,retry,continuation);
}
static void install_reply_observer(void) {
    Class cls=objc_getClass("CFPrefsPlistSource");
    SEL selector=sel_registerName("handleErrorReply:toMessage:settingKeys:toValues:count:retryCount:retryContinuation:");
    Method method=cls ? class_getInstanceMethod(cls,selector) : NULL;
    if(!method || method_getNumberOfArguments(method)!=9){puts("M39C observer unavailable: method/arity");fail(160);}
    char ret[16],count_type[16],retry_type[16],arg[16];
    method_getReturnType(method,ret,sizeof(ret));
    method_getArgumentType(method,6,count_type,sizeof(count_type));
    method_getArgumentType(method,7,retry_type,sizeof(retry_type));
    printf("M39C observer encoding=%s\n",method_getTypeEncoding(method));
    if(ret[0]!='v' || (count_type[0]!='q' && count_type[0]!='Q') || (retry_type[0]!='i' && retry_type[0]!='I'))fail(161);
    for(unsigned i=2;i<=5;i++){
        method_getArgumentType(method,i,arg,sizeof(arg));
        /* const qualifiers may precede pointer types for the key/value arrays. */
        const char *t=arg;while(*t=='r')t++;
        if(i<=3 ? *t!='@' : *t!='^')fail(161);
    }
    method_getArgumentType(method,8,arg,sizeof(arg));if(arg[0]!='@')fail(161);
    describe_xpc=(char *(*)(void *))dlsym(RTLD_DEFAULT,"xpc_copy_description");
    if(!describe_xpc)fail(162);
    original_error=(prefs_error_imp)method_getImplementation(method);
    if(!original_error)fail(163);
    IMP replaced=method_setImplementation(method,(IMP)observe_preferences_error);
    if(replaced!=(IMP)original_error)fail(164);
    puts("M39C observer ready: errors logged then original handler called");
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
    if (!CFPreferencesSynchronize(app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost)) fail(145);
    CFPropertyListRef value=CFPreferencesCopyValue(key,app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    if (!value || CFGetTypeID(value)!=CFStringGetTypeID() || !CFEqual(value,CFSTR("m39-independent-read"))) fail(146);
    CFRelease(value);
    puts("XCOVER5 M39 READER PASS: fresh exec read expected preference");
    return 59;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0); setvbuf(stderr,NULL,_IONBF,0);
    alarm(60);
    app=CFSTR("org.xcover5.m39"); key=CFSTR("proof");
    if (argc==2 && !strcmp(argv[1],"--read")) return reader();
    if (getppid()!=1 || getuid()!=0) fail(140);
    printf("M39A ID uid=%u euid=%u gid=%u ppid=%d HOME=%s\n",(unsigned)getuid(),(unsigned)geteuid(),(unsigned)getgid(),getppid(),getenv("HOME")?getenv("HOME"):"(unset)");
    struct passwd *account=getpwuid(geteuid());
    printf("M39A ACCOUNT home=%s\n",account?account->pw_dir:"(lookup failed)");
    filesystem_probe("/var/root/Library/Preferences");
    filesystem_probe("/Library/Preferences");
    install_reply_observer();
    puts("XCOVER5 M39 BEGIN: cfprefsd bootstrap lookup");
    mach_port_t port=MACH_PORT_NULL;
    kern_return_t kr=bootstrap_look_up(bootstrap_port,"com.apple.cfprefsd.daemon",&port);
    if (kr!=KERN_SUCCESS || !MACH_PORT_VALID(port)) { fprintf(stderr,"M39 bootstrap kr=%d\n",kr); fail(141); }
    mach_port_deallocate(mach_task_self(),port);
    puts("XCOVER5 M39: daemon port acquired, writing preference");
    CFPreferencesSetValue(key,CFSTR("m39-independent-read"),app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    errno=0;
    Boolean synced=CFPreferencesSynchronize(app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    printf("M39A SYNC returned=%d (errno is not a CFPreferences error code)\n",synced);
    if (!synced) fail(142);
    struct stat st;
    if (stat("/var/root/Library/Preferences/org.xcover5.m39.plist",&st) || !S_ISREG(st.st_mode) || st.st_size<=0) fail(143);
    puts("XCOVER5 M39: preference synchronized to RAM filesystem, starting fresh reader");
    pid_t child=fork();
    if(child<0) fail(144);
    if(!child) { execl("/sbin/m39-probe","m39-probe","--read",(char*)NULL); fail(147); }
    int status=0; pid_t got;
    do { got=waitpid(child,&status,0); } while(got<0 && errno==EINTR);
    if(got!=child || !WIFEXITED(status) || WEXITSTATUS(status)!=59) { fprintf(stderr,"M39 reader status=%x\n",status); fail(148); }
    CFPreferencesSetValue(key,NULL,app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    if (!CFPreferencesSynchronize(app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost)) fail(149);
    CFPropertyListRef removed=CFPreferencesCopyValue(key,app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    if(removed) { CFRelease(removed); fail(150); }
    puts("XCOVER5 M39 PASS: preferences write + sync + file + fresh exec read + cleanup (RAM only)");
    return 60;
}
