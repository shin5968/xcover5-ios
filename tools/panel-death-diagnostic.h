/* M50A independent bounded progress transport; caller preserves original errno. */
#ifndef XCOVER_PANEL_DEATH_DIAGNOSTIC_H
#define XCOVER_PANEL_DEATH_DIAGNOSTIC_H
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
struct m50a_event {uint32_t phase,pid;int32_t result,error;};
static void m50a_event_write(int fd,unsigned phase,int result,int error) {
 if(fd<0)return;
 int kept=errno;struct m50a_event e={phase,(uint32_t)getpid(),result,error};
 ssize_t n;do{n=write(fd,&e,sizeof(e));}while(n<0 && errno==EINTR);
 (void)n;errno=kept;
}
static void m50a_event_drain(int fd,struct m50a_event *last,unsigned *flags) {
 if(fd<0)return;
 int kept=errno;struct m50a_event e;ssize_t n;
 for(;;) {
  do{n=read(fd,&e,sizeof(e));}while(n<0 && errno==EINTR);
  if(n==(ssize_t)sizeof(e)) {
   if(e.phase>=1 && e.phase<=16 && e.pid>1 && e.pid<=0x7fffffffU && e.error>=0 && e.error<=1024)*last=e;
   else *flags|=4;
  }else {if(n==0)*flags|=2;else if(n>0 || errno!=EAGAIN)*flags|=4;break;}
 }
 errno=kept;
}
#endif
