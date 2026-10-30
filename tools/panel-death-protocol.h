/* M50 pipe-only control: process IDs and surface IDs, no user pointers. */
#ifndef XCOVER_PANEL_DEATH_PROTOCOL_H
#define XCOVER_PANEL_DEATH_PROTOCOL_H
#include <stdint.h>
#include <unistd.h>
#include <poll.h>
#include <errno.h>
enum {M50_STARTED=0x50353050,M50_HELD=0x50353048};
struct m50_packet {uint32_t type,pid,sid,last;};
static int m50_send(int fd,const struct m50_packet *p) {
 ssize_t n;do{n=write(fd,p,sizeof(*p));}while(n<0 && errno==EINTR);
 return n==(ssize_t)sizeof(*p)?0:-1;
}
static int m50_receive(int fd,struct m50_packet *p,int timeout) {
 size_t at=0;
 while(at<sizeof(*p)) {
  struct pollfd event={.fd=fd,.events=POLLIN};int rc;
  do{rc=poll(&event,1,timeout);}while(rc<0 && errno==EINTR);
  if(rc<=0){if(!rc)errno=ETIMEDOUT;return -1;}
  ssize_t n;do{n=read(fd,(char*)p+at,sizeof(*p)-at);}while(n<0 && errno==EINTR);
  if(n<=0){if(!n)errno=EPROTO;return -1;}at+=(size_t)n;
 }
 return 0;
}
static int m50_restore_valid(const uint64_t before[7],const uint64_t after[7],uint32_t pid) {
 return before[1]==0 && after[0]==before[0]+1 && after[1]==0 && after[2]==pid &&
  after[3]==1 && after[4]==4 && after[5]==0 && after[6]==3;
}
#endif
