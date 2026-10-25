/* M39: real CoreFoundation APIs, separate exec reader, and RAM-root file check. */
#include <CoreFoundation/CoreFoundation.h>
#include <servers/bootstrap.h>
#include <mach/mach.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static CFStringRef app, key;
static void fail(int stage) { fprintf(stderr,"XCOVER5 M39 FAIL stage=%d errno=%d\n",stage,errno); _exit(stage); }
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
    puts("XCOVER5 M39 BEGIN: cfprefsd bootstrap lookup");
    mach_port_t port=MACH_PORT_NULL;
    kern_return_t kr=bootstrap_look_up(bootstrap_port,"com.apple.cfprefsd.daemon",&port);
    if (kr!=KERN_SUCCESS || !MACH_PORT_VALID(port)) { fprintf(stderr,"M39 bootstrap kr=%d\n",kr); fail(141); }
    mach_port_deallocate(mach_task_self(),port);
    puts("XCOVER5 M39: daemon port acquired, writing preference");
    CFPreferencesSetValue(key,CFSTR("m39-independent-read"),app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
    if (!CFPreferencesSynchronize(app,kCFPreferencesCurrentUser,kCFPreferencesAnyHost)) fail(142);
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
