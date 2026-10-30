/* M50: actual orphan-task SIGKILL cleanup followed by fresh M49 session. */
#include "m49-baseline.c"
#include "panel-death-protocol.h"
#include "panel-death-diagnostic.h"
static pid_t m50_orphan=-1;

static pid_t m50_middle=-1;
static int m50_diag_write=-1,m50_diag_read=-1,m50_parent_active,m50_middle_status;
static unsigned m50_stage,m50_child_phase,m50_diag_flags;
static mach_port_t m50_observer;
static struct m50a_event m50_last_event;
static struct m50_packet m50_packet_state;
static void m50_progress(unsigned phase,int result,int error) {
 m50_child_phase=phase;m50a_event_write(m50_diag_write,phase,result,error);
}
static int m50a_receive(int fd,struct m50_packet *p,int timeout) {
 memset(p,0,sizeof(*p));int rc=m50_receive(fd,p,timeout);m50_packet_state=*p;return rc;
}
static void m50_publish_failure(int error) {
 if(!m50_parent_active)return;
 m50a_event_drain(m50_diag_read,&m50_last_event,&m50_diag_flags);
 uint64_t v[20]={m50_stage,(uint32_t)error,m50_orphan>1?(uint32_t)m50_orphan:0,
  m50_middle>1?(uint32_t)m50_middle:0,m50_last_event.phase,m50_last_event.pid,
  (uint32_t)m50_last_event.result,(uint32_t)m50_last_event.error,
  (uint32_t)m50_trace.poll_rc,(uint32_t)m50_trace.poll_errno,m50_trace.revents,
  (uint32_t)m50_trace.read_rc,(uint32_t)m50_trace.read_errno,m50_trace.bytes,
  m50_packet_state.type,m50_packet_state.pid,m50_packet_state.sid,m50_packet_state.last,
  (uint32_t)m50_middle_status,m50_diag_flags};
 fprintf(stderr,"XCOVER5 M50A FAIL stage=%u errno=%d child_phase=%u child_pid=%u poll=%d read=%d bytes=%u\n",
  m50_stage,error,m50_last_event.phase,m50_last_event.pid,m50_trace.poll_rc,m50_trace.read_rc,m50_trace.bytes);
 if(m50_observer){uint32_t n=0;int rc=io.call(m50_observer,95,NULL,0,v,sizeof(v),NULL,&n,NULL,NULL);
  fprintf(stderr,"M50A diagnostic publish rc=%x\n",rc);}
}

static void m50_fail(const char *where) {
 int kept=errno;
 if(m50_diag_write>=0)m50_progress(m50_child_phase,-1,kept);
 m50_publish_failure(kept);errno=kept;
 fprintf(stderr,"XCOVER5 M50 FAIL where=%s errno=%d orphan=%d\n",where,errno,m50_orphan);
 if(m50_orphan>1)kill(m50_orphan,SIGKILL);
 _exit(87);
}
static int m50_fd(const char *text) {
 char *end=NULL;errno=0;long fd=strtol(text,&end,10);
 if(errno || !end || *end || fd<0 || fd>INT_MAX)m50_fail("fd_argument");
 return (int)fd;
}
static int m50_detach(const char *self,int fd,const char *fd_text,const char *diag_text) {
 m50_progress(2,0,0);
 pid_t pid=fork();if(pid<0)m50_fail("detach_fork");
 if(pid>0)_exit(0);
 alarm(20);m50_progress(3,0,0);
 struct m50_packet started={M50_STARTED,(uint32_t)getpid(),0,0};
 m50_progress(4,0,0);int sent=m50_send(fd,&started),send_errno=sent?errno:0;
 m50_progress(5,sent,send_errno);if(sent)_exit(88);
 unsigned tries;for(tries=0;tries<100 && getppid()!=1;tries++)usleep(50000);
 if(getppid()!=1){m50_progress(6,-1,ETIMEDOUT);_exit(88);}
 m50_progress(6,0,0);
 m50_progress(7,0,0);execl(self,self,"--m50-death-child",fd_text,diag_text,(char*)NULL);m50_progress(7,-1,errno);_exit(88);
}
static int m50_death_child(int fd) {
 m50_progress(8,0,0);alarm(20);
 if(getuid()!=0 || getppid()!=1)m50_fail("orphan_identity");
 m50_progress(9,0,0);load_api();load_io();load_fb();m50_progress(10,0,0);
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer"));
 void *display=NULL;
 if(!svc || fb.open(svc,mach_task_self(),0,&display) || !display)m50_fail("child_open");
 io.release(svc);m50_progress(11,0,0);
 CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
 number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
 Surface s=api.IOSurfaceCreate(d);CFRelease(d);
 if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 || api.IOSurfaceGetBytesPerRow(s)!=2880 ||
    api.IOSurfaceGetPixelFormat(s)!=0x42475241 || api.IOSurfaceGetAllocSize(s)<M48_BYTES)m50_fail("child_surface");
 uint32_t sid=api.IOSurfaceGetID(s);if(!sid)m50_fail("child_id");m50_progress(12,0,0);
 m50_progress(13,0,0);for(unsigned frame=0;frame<3;frame++) {
  lock_surface(s,0,0);uint32_t *p=api.IOSurfaceGetBaseAddress(s);if(!p)m50_fail("child_mapping");
  for(unsigned y=0;y<1480;y++)for(unsigned x=0;x<720;x++) {
   uint32_t color=frame==0?0xff00ffffU:frame==1?0xffff00ffU:(x>=270 && x<450?0xffffff00U:0xffff00ffU);
   if(x<4 || x>=716 || y<4 || y>=1476)color=0xffffffffU;p[y*720+x]=color;
  }
  uint64_t hash=full_hash(p);lock_surface(s,0,1);
  uint32_t seq=0;if(fb.begin(display,&seq) || seq!=frame+1)m50_fail("child_sequence");
  if(!fb.wait(display,seq,0))m50_fail("child_premature_wait");
  FBRect rect={0,0,720,1480};
  if(fb.layer(display,0,s,rect,rect,0) || fb.end(display) || fb.wait(display,seq,0))m50_fail("child_submit");
  lock_surface(s,1,0);p=api.IOSurfaceGetBaseAddress(s);
  if(!p || full_hash(p)!=hash)m50_fail("child_source_changed");lock_surface(s,1,1);
 }
 m50_progress(14,0,0);mach_port_t mark_service=io.service(0,io.matching("IOMobileFramebuffer")),mark=0;
 if(!mark_service || io.open(mark_service,mach_task_self(),0,&mark) || !mark)m50_fail("child_mark_open");
 io.release(mark_service);uint32_t no_output=0;
 if(io.call(mark,94,NULL,0,NULL,0,NULL,&no_output,NULL,NULL))m50_fail("child_mark");
 io.close(mark);
 struct m50_packet held={M50_HELD,(uint32_t)getpid(),sid,3};
 m50_progress(15,0,0);int sent=m50_send(fd,&held),send_errno=sent?errno:0;
 m50_progress(16,sent,send_errno);if(sent){errno=send_errno;m50_fail("child_held_write");}
 /* Deliberately no CFRelease/IOServiceClose: observer must kill this task. */
 for(;;)pause();
}
static void m50_run_death(const char *self) {
 m50_parent_active=1;m50_stage=1;m50_trace=(struct m50_wait_trace){.poll_rc=-2,.read_rc=-2};alarm(30);
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer")),control=0;
 if(!svc || io.open(svc,mach_task_self(),0,&control) || !control)m50_fail("observer_open");io.release(svc);
 m50_observer=control;uint64_t before[7]={0};persistent_status(control,before);if(before[1])m50_fail("already_active");
 int pipefd[2];if(pipe(pipefd))m50_fail("pipe");
 int diagnostic[2];if(pipe(diagnostic))m50_fail("diagnostic_pipe");
 int flags=fcntl(diagnostic[0],F_GETFL);
 if(flags<0 || fcntl(diagnostic[0],F_SETFL,flags|O_NONBLOCK)<0)m50_fail("diagnostic_nonblock");
 m50_diag_read=diagnostic[0];
 char fd_text[24],diag_text[24];snprintf(fd_text,sizeof(fd_text),"%d",pipefd[1]);snprintf(diag_text,sizeof(diag_text),"%d",diagnostic[1]);m50_stage=2;
 pid_t middle=fork();if(middle<0)m50_fail("fork");
 if(!middle){close(pipefd[0]);close(diagnostic[0]);m50_parent_active=0;m50_diag_write=diagnostic[1];
  if(signal(SIGPIPE,SIG_IGN)==SIG_ERR)_exit(88);m50_progress(1,0,0);
  execl(self,self,"--m50-detach",fd_text,diag_text,(char*)NULL);m50_progress(1,-1,errno);_exit(88);}
 m50_middle=middle;close(diagnostic[1]);m50_stage=3;
 close(pipefd[1]);struct m50_packet p={0};
 if(m50a_receive(pipefd[0],&p,15000) || p.type!=M50_STARTED || p.pid<=1 || p.pid>INT_MAX || p.pid==(uint32_t)getpid() || p.sid || p.last)m50_fail("started_packet");
 m50_orphan=(pid_t)p.pid;m50_stage=4;
 int status=0;pid_t got=0;
 for(unsigned tries=0;tries<100;tries++){got=waitpid(middle,&status,WNOHANG);m50_middle_status=status;if(got==middle)break;if(got<0 && errno!=EINTR)m50_fail("detach_wait");usleep(50000);}
 if(got!=middle || !WIFEXITED(status) || WEXITSTATUS(status))m50_fail("detach_status");
 m50_stage=5;
 if(m50a_receive(pipefd[0],&p,15000) || p.type!=M50_HELD || p.pid!=(uint32_t)m50_orphan || !p.sid || p.sid>=256 || p.last!=3)m50_fail("held_packet");
 m50_stage=6;uint64_t active[7]={0};persistent_status(control,active);
 if(active[0]!=before[0] || active[1]!=1)m50_fail("not_held");
 usleep(1000000);persistent_status(control,active);
 if(active[0]!=before[0] || active[1]!=1)m50_fail("hold_lost");
 m50_stage=7;pid_t victim=m50_orphan;
 if(kill(victim,SIGKILL))m50_fail("kill");m50_orphan=-1;
 m50_stage=8;m50_trace=(struct m50_wait_trace){.poll_rc=-2,.read_rc=-2};
 struct pollfd event={.fd=pipefd[0],.events=POLLIN};int n;
 do{n=poll(&event,1,10000);}while(n<0 && errno==EINTR);
 m50_trace.poll_rc=n;m50_trace.poll_errno=n<0?errno:0;m50_trace.revents=(unsigned short)event.revents;
 char extra=0;ssize_t end=-2;if(n==1){do{end=read(pipefd[0],&extra,1);}while(end<0 && errno==EINTR);}
 m50_trace.read_rc=(int)end;m50_trace.read_errno=end==-1?errno:0;
 if(n!=1 || end!=0)m50_fail("death_pipe_eof");close(pipefd[0]);
 m50_stage=9;uint64_t after[7]={0};unsigned tries;
 for(tries=0;tries<100;tries++){persistent_status(control,after);if(after[0]!=before[0])break;usleep(50000);}
 if(tries==100 || !m50_restore_valid(before,after,(uint32_t)victim))m50_fail("death_restore");
 m50_stage=10;int released=0;
 for(tries=0;tries<100;tries++){Surface found=api.IOSurfaceLookup(p.sid);if(!found){released=1;break;}CFRelease(found);usleep(50000);}
 if(!released)m50_fail("death_surface_leak");
 printf("XCOVER5 M50 DEATH PASS owner=%d sid=%u frames=1 last=3 reason=4 restored=0 surface_gone=1\n",victim,p.sid);
 m50_orphan=-1;close(m50_diag_read);m50_diag_read=-1;m50_observer=0;io.close(control);
}
int main(int argc,char **argv) {
 setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
 if(argc==4 && (!strcmp(argv[1],"--m50-detach") || !strcmp(argv[1],"--m50-death-child"))) {
  m50_diag_write=m50_fd(argv[3]);if(signal(SIGPIPE,SIG_IGN)==SIG_ERR)m50_fail("sigpipe_disposition");
  if(!strcmp(argv[1],"--m50-detach"))return m50_detach(argv[0],m50_fd(argv[2]),argv[2],argv[3]);
  return m50_death_child(m50_fd(argv[2]));
 }
 int result=m49_baseline_main(argc,argv);if(argc!=1 || result!=71)return result;
 m50_run_death(argv[0]);
 m50_stage=11;if(run_persistent()!=71)m50_fail("recovery_session");
 puts("XCOVER5 M50 PASS:original M49 + SIGKILL/clientDied restore and surface cleanup + fresh repeated M49 session");
 return 72;
}
