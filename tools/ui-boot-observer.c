/* M55 observation endpoint. Real UI jobs are started by Apple launchd. */
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
 printf("XCOVER5 M55 BEGIN observer pid=%d ppid=%d uid=%d; real launchd mobile UI jobs; no graphics baseline delay\n",getpid(),getppid(),getuid());
 const char *paths[]={"/usr/libexec/backboardd","/System/Library/CoreServices/SpringBoard.app/SpringBoard"};
 const off_t sizes[]={1182960,112048};
 for(unsigned i=0;i<2;i++){
  struct stat st;errno=0;int rc=stat(paths[i],&st),error=errno;
  printf("XCOVER5 M55 FILE path=%s stat=%d errno=%d size=%lld expected=%lld\n",paths[i],rc,error,rc?-1LL:(long long)st.st_size,(long long)sizes[i]);
  if(rc || st.st_size!=sizes[i])return 201;
  int fd=open(paths[i],O_RDONLY);uint32_t magic=0;ssize_t n=fd<0?-1:read(fd,&magic,sizeof magic);if(fd>=0)close(fd);
  printf("XCOVER5 M55 MACHO path=%s bytes=%ld magic=%08x\n",paths[i],(long)n,magic);
  if(n!=4 || (magic!=0xfeedfacfU && magic!=0xbebafecaU && magic!=0xbfbafecaU))return 202;
 }
 for(unsigned elapsed=0;elapsed<45;elapsed++){
  if(elapsed%5==0)printf("XCOVER5 M55 OBSERVE elapsed=%u; inspect launchd/backboardd/SpringBoard messages\n",elapsed);
  sleep(1);
 }
 puts("XCOVER5 M55 OBSERVATION_END:45 seconds; exit77 means capture complete ONLY; not UI readiness or lock-screen success");
 return 77;
}
