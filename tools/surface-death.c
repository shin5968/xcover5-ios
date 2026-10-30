/* M50: actual orphan-task SIGKILL cleanup followed by fresh M49 session. */
#include "m49-baseline.c"
#include "panel-death-protocol.h"
static pid_t m50_orphan=-1;
static void m50_fail(const char *where) {
 fprintf(stderr,"XCOVER5 M50 FAIL where=%s errno=%d orphan=%d\n",where,errno,m50_orphan);
 if(m50_orphan>1)kill(m50_orphan,SIGKILL);
 _exit(87);
}
static int m50_fd(const char *text) {
 char *end=NULL;errno=0;long fd=strtol(text,&end,10);
 if(errno || !end || *end || fd<0 || fd>INT_MAX)m50_fail("fd_argument");
 return (int)fd;
}
static int m50_detach(const char *self,int fd,const char *fd_text) {
 pid_t pid=fork();if(pid<0)m50_fail("detach_fork");
 if(pid>0)_exit(0);
 alarm(20);
 struct m50_packet started={M50_STARTED,(uint32_t)getpid(),0,0};
 if(m50_send(fd,&started))_exit(88);
 unsigned tries;for(tries=0;tries<100 && getppid()!=1;tries++)usleep(50000);
 if(getppid()!=1)_exit(88);
 execl(self,self,"--m50-death-child",fd_text,(char*)NULL);_exit(88);
}
static int m50_death_child(int fd) {
 alarm(20);
 if(getuid()!=0 || getppid()!=1)m50_fail("orphan_identity");
 load_api();load_io();load_fb();
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer"));
 void *display=NULL;
 if(!svc || fb.open(svc,mach_task_self(),0,&display) || !display)m50_fail("child_open");
 io.release(svc);
 CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
 number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
 Surface s=api.IOSurfaceCreate(d);CFRelease(d);
 if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 || api.IOSurfaceGetBytesPerRow(s)!=2880 ||
    api.IOSurfaceGetPixelFormat(s)!=0x42475241 || api.IOSurfaceGetAllocSize(s)<M48_BYTES)m50_fail("child_surface");
 uint32_t sid=api.IOSurfaceGetID(s);if(!sid)m50_fail("child_id");
 for(unsigned frame=0;frame<3;frame++) {
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
 mach_port_t mark_service=io.service(0,io.matching("IOMobileFramebuffer")),mark=0;
 if(!mark_service || io.open(mark_service,mach_task_self(),0,&mark) || !mark)m50_fail("child_mark_open");
 io.release(mark_service);uint32_t no_output=0;
 if(io.call(mark,94,NULL,0,NULL,0,NULL,&no_output,NULL,NULL))m50_fail("child_mark");
 io.close(mark);
 struct m50_packet held={M50_HELD,(uint32_t)getpid(),sid,3};
 if(m50_send(fd,&held))m50_fail("child_held_write");
 /* Deliberately no CFRelease/IOServiceClose: observer must kill this task. */
 for(;;)pause();
}
static void m50_run_death(const char *self) {
 alarm(30);
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer")),control=0;
 if(!svc || io.open(svc,mach_task_self(),0,&control) || !control)m50_fail("observer_open");io.release(svc);
 uint64_t before[7]={0};persistent_status(control,before);if(before[1])m50_fail("already_active");
 int pipefd[2];if(pipe(pipefd))m50_fail("pipe");
 char fd_text[24];snprintf(fd_text,sizeof(fd_text),"%d",pipefd[1]);
 pid_t middle=fork();if(middle<0)m50_fail("fork");
 if(!middle){close(pipefd[0]);execl(self,self,"--m50-detach",fd_text,(char*)NULL);_exit(88);}
 close(pipefd[1]);struct m50_packet p={0};
 if(m50_receive(pipefd[0],&p,15000) || p.type!=M50_STARTED || p.pid<=1 || p.pid>INT_MAX || p.pid==(uint32_t)getpid() || p.sid || p.last)m50_fail("started_packet");
 m50_orphan=(pid_t)p.pid;
 int status=0;pid_t got=0;
 for(unsigned tries=0;tries<100;tries++){got=waitpid(middle,&status,WNOHANG);if(got==middle)break;if(got<0 && errno!=EINTR)m50_fail("detach_wait");usleep(50000);}
 if(got!=middle || !WIFEXITED(status) || WEXITSTATUS(status))m50_fail("detach_status");
 if(m50_receive(pipefd[0],&p,15000) || p.type!=M50_HELD || p.pid!=(uint32_t)m50_orphan || !p.sid || p.sid>=256 || p.last!=3)m50_fail("held_packet");
 uint64_t active[7]={0};persistent_status(control,active);
 if(active[0]!=before[0] || active[1]!=1)m50_fail("not_held");
 usleep(1000000);persistent_status(control,active);
 if(active[0]!=before[0] || active[1]!=1)m50_fail("hold_lost");
 pid_t victim=m50_orphan;
 if(kill(victim,SIGKILL))m50_fail("kill");m50_orphan=-1;
 struct pollfd event={.fd=pipefd[0],.events=POLLIN};int n;
 do{n=poll(&event,1,10000);}while(n<0 && errno==EINTR);
 char extra=0;ssize_t end=-1;if(n==1){do{end=read(pipefd[0],&extra,1);}while(end<0 && errno==EINTR);}
 if(n!=1 || end!=0)m50_fail("death_pipe_eof");close(pipefd[0]);
 uint64_t after[7]={0};unsigned tries;
 for(tries=0;tries<100;tries++){persistent_status(control,after);if(after[0]!=before[0])break;usleep(50000);}
 if(tries==100 || !m50_restore_valid(before,after,(uint32_t)victim))m50_fail("death_restore");
 int released=0;
 for(tries=0;tries<100;tries++){Surface found=api.IOSurfaceLookup(p.sid);if(!found){released=1;break;}CFRelease(found);usleep(50000);}
 if(!released)m50_fail("death_surface_leak");
 printf("XCOVER5 M50 DEATH PASS owner=%d sid=%u frames=1 last=3 reason=4 restored=0 surface_gone=1\n",victim,p.sid);
 m50_orphan=-1;io.close(control);
}
int main(int argc,char **argv) {
 setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
 if(argc==3 && !strcmp(argv[1],"--m50-detach"))return m50_detach(argv[0],m50_fd(argv[2]),argv[2]);
 if(argc==3 && !strcmp(argv[1],"--m50-death-child"))return m50_death_child(m50_fd(argv[2]));
 int result=m49_baseline_main(argc,argv);if(argc!=1 || result!=71)return result;
 m50_run_death(argv[0]);
 if(run_persistent()!=71)m50_fail("recovery_session");
 puts("XCOVER5 M50 PASS:original M49 + SIGKILL/clientDied restore and surface cleanup + fresh repeated M49 session");
 return 72;
}
