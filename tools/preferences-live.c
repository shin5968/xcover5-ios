/* M40: explicit notifyd wakeup plus cached CFPreferences coherence.
 * The notification is posted by this test AFTER real CF synchronization.
 * This does not claim automatic CoreFoundation notification delivery. */
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#include <notify.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <poll.h>
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int m39_baseline_main(int,char **);
static const char notice[]="org.xcover5.m39.live-change";
static CFStringRef domain,live_key;
static pid_t live_child=-1;
static int writer_role;
static void fail(int stage,const char *where) {
    fprintf(stderr,"XCOVER5 M40 FAIL stage=%d where=%s errno=%d\n",stage,where,errno);
    if(writer_role){
        if(live_child>0){kill(live_child,SIGKILL);while(waitpid(live_child,NULL,0)<0 && errno==EINTR){};}
        CFPreferencesSetAppValue(live_key,NULL,domain);
        fprintf(stderr,"M40 failure cleanup sync=%d\n",(int)CFPreferencesAppSynchronize(domain));
    }
    _exit(stage);
}
static int equals(CFStringRef expected) {
    CFPropertyListRef value=CFPreferencesCopyAppValue(live_key,domain);
    int ok=expected?(value && CFGetTypeID(value)==CFStringGetTypeID() && CFEqual(value,expected)):value==NULL;
    if(value)CFRelease(value);
    return ok;
}
static void set_value(CFStringRef value,int stage) {
    CFPreferencesSetAppValue(live_key,value,domain);
    if(!CFPreferencesAppSynchronize(domain))fail(stage,"writer_sync");
    if(!equals(value))fail(stage,"writer_value");
}
static void ack(int fd,char value) {
    ssize_t n;do{n=write(fd,&value,1);}while(n<0&&errno==EINTR);
    if(n!=1)fail(163,"reader_ack_write");
}
static void expect_ack(int fd,char expected,int stage) {
    struct pollfd p={.fd=fd,.events=POLLIN};int n;
    do{n=poll(&p,1,15000);}while(n<0&&errno==EINTR);
    if(n!=1)fail(stage,"parent_ack_timeout");
    char value=0;ssize_t got;do{got=read(fd,&value,1);}while(got<0&&errno==EINTR);
    if(got!=1 || value!=expected)fail(stage,"parent_ack_or_child_exit");
}
static void receive_phase(mach_port_t port,int token,CFStringRef expected,int stage) {
    int notified=0;
    for(unsigned attempt=0;attempt<10;attempt++){
        union {mach_msg_header_t h;unsigned char bytes[512];} message;
        memset(&message,0,sizeof(message));
        mach_msg_return_t kr=mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,500,MACH_PORT_NULL);
        if(kr==MACH_MSG_SUCCESS){
            if((message.h.msgh_bits&MACH_MSGH_BITS_COMPLEX) || message.h.msgh_size!=sizeof(mach_msg_header_t) ||
               message.h.msgh_local_port!=port || message.h.msgh_id!=token)fail(170,"notify_message_shape_or_token");
            notified=1;
        }else if(kr!=MACH_RCV_TIMED_OUT){fprintf(stderr,"M40 mach receive kr=%x\n",kr);fail(171,"notify_receive");}
        /* No explicit CF synchronize after READY: test this process's cached source. */
        if(notified && equals(expected))return;
    }
    if(!notified)fail(172,"notify_delivery_timeout");
    Boolean refreshed=CFPreferencesAppSynchronize(domain);
    fprintf(stderr,"M40 STALE diagnostic_only explicit_sync=%d value_after_sync=%d\n",(int)refreshed,equals(expected));
    fail(stage,"cached_value_not_updated"); /* A refresh cannot convert failure to PASS. */
}
static int live_reader(int fd) {
    alarm(35);
    int token=-1;mach_port_t port=MACH_PORT_NULL;
    uint32_t rc=notify_register_mach_port(notice,&port,0,&token);
    if(rc!=NOTIFY_STATUS_OK || !MACH_PORT_VALID(port)){fprintf(stderr,"M40 notify register rc=%u\n",rc);fail(164,"notify_register");}
    if(!CFPreferencesAppSynchronize(domain) || !equals(CFSTR("A")))fail(165,"reader_initial_A");
    printf("XCOVER5 M40 READER READY pid=%d cached=A token=%d\n",getpid(),token);
    ack(fd,'R');
    receive_phase(port,token,CFSTR("B"),173);
    puts("XCOVER5 M40 READER UPDATE: notify received, cached=B without explicit sync");
    ack(fd,'B');
    receive_phase(port,token,NULL,174);
    puts("XCOVER5 M40 READER DELETE: notify received, cached key absent without explicit sync");
    if(notify_cancel(token)!=NOTIFY_STATUS_OK)fail(175,"notify_cancel");
    ack(fd,'D');close(fd);
    puts("XCOVER5 M40 READER PASS: same PID A-to-B-to-absent + two notify messages + cancel");
    return 61;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
    domain=CFSTR("org.xcover5.m39");live_key=CFSTR("live-proof");
    if(argc==3 && !strcmp(argv[1],"--m40-reader")){
        char *end=NULL;errno=0;long fd=strtol(argv[2],&end,10);
        if(errno || !end || *end || fd<0 || fd>INT_MAX)fail(160,"reader_fd_argument");
        return live_reader((int)fd);
    }
    int baseline=m39_baseline_main(argc,argv);
    if(argc!=1 || baseline!=60)return baseline;
    alarm(45);
#ifndef M40_HOST_TEST
    if(getuid()!=0 || getppid()!=1)fail(161,"writer_identity");
#endif
    writer_role=1;
    puts("XCOVER5 M40 BEGIN: explicit notifyd wakeup + live reader cache coherence (RAM only)");
    set_value(CFSTR("A"),162);
    int pipefd[2];if(pipe(pipefd))fail(166,"pipe");
    live_child=fork();if(live_child<0)fail(167,"fork");
    if(!live_child){
        writer_role=0;close(pipefd[0]);char fd[24];snprintf(fd,sizeof(fd),"%d",pipefd[1]);
#ifdef M40_HOST_TEST
        execl(argv[0],argv[0],"--m40-reader",fd,(char*)NULL);
#else
        execl("/sbin/m39-probe","m39-probe","--m40-reader",fd,(char*)NULL);
#endif
        fail(168,"exec_live_reader");
    }
    close(pipefd[1]);expect_ack(pipefd[0],'R',176);
    set_value(CFSTR("B"),177);
#ifdef M40_HOST_TEST
    if(!getenv("M40_TEST_SKIP_POST"))
#endif
    if(notify_post(notice)!=NOTIFY_STATUS_OK)fail(178,"post_B");
    expect_ack(pipefd[0],'B',179);
    set_value(NULL,180);
    if(notify_post(notice)!=NOTIFY_STATUS_OK)fail(181,"post_delete");
    expect_ack(pipefd[0],'D',182);close(pipefd[0]);
    int status=0;pid_t got=0;
    for(unsigned attempt=0;attempt<100;attempt++){
        got=waitpid(live_child,&status,WNOHANG);
        if(got==live_child)break;
        if(got<0 && errno!=EINTR)fail(183,"waitpid");
        usleep(50000);
    }
    if(got!=live_child)fail(184,"child_exit_timeout");
    live_child=-1;
    if(!WIFEXITED(status) || WEXITSTATUS(status)!=61){fprintf(stderr,"M40 reader status=%x\n",status);fail(185,"child_status");}
    if(!equals(NULL))fail(186,"final_cleanup_value");
    puts("XCOVER5 M40 PASS: original M39 + two live processes + notify wakeups + cached update/delete + cleanup (RAM only)");
    return 62;
}
