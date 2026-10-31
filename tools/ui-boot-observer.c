/* M55 observation endpoint. Real UI jobs are started by Apple launchd. */
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#if defined(M66_ICU_PROFILE)
#include "m66-icu-probe.h"
#endif
#if defined(M63_RESOURCE_PROFILE)
#include <sys/mount.h>
static void resource_status(unsigned elapsed){
 struct statfs fs;errno=0;int rc=statfs("/",&fs),error=errno;
 printf("XCOVER5 M63 SPACE elapsed=%u statfs=%d errno=%d total=%llu free=%llu available=%llu block=%u\n",elapsed,rc,error,rc?0ULL:(unsigned long long)fs.f_blocks,rc?0ULL:(unsigned long long)fs.f_bfree,rc?0ULL:(unsigned long long)fs.f_bavail,rc?0U:(unsigned)fs.f_bsize);
 const char *paths[]={"/var/installd","/var/db/analyticsd","/var/db/diagnostics/.migrated","/var/db/diagnostics/timesync/.migrated","/var/db/uuidtext/.migrated","/System/Library/LifecyclePolicy/DomainAttributes/com.apple.frontboard.plist"};
 for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);i++){
  struct stat st;errno=0;rc=stat(paths[i],&st);error=errno;
  printf("XCOVER5 M63 RESOURCE elapsed=%u path=%s stat=%d errno=%d uid=%u gid=%u mode=%o bytes=%lld\n",elapsed,paths[i],rc,error,rc?0U:st.st_uid,rc?0U:st.st_gid,rc?0U:(st.st_mode&07777),rc?-1LL:(long long)st.st_size);
 }
}
#define OBSERVATION_SECONDS 90
#else
#define OBSERVATION_SECONDS 45
#endif
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
 printf("XCOVER5 M55 BEGIN observer pid=%d ppid=%d uid=%d; real launchd mobile UI jobs; no graphics baseline delay\n",getpid(),getppid(),getuid());
#if defined(M66_ICU_PROFILE)
 m66_icu_probe();
#endif
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
 for(unsigned elapsed=0;elapsed<OBSERVATION_SECONDS;elapsed++){
#if defined(M63_RESOURCE_PROFILE)
  if(elapsed%30==0)resource_status(elapsed);
#endif
  if(elapsed%5==0)printf("XCOVER5 M55 OBSERVE elapsed=%u; inspect launchd/backboardd/SpringBoard messages\n",elapsed);
  sleep(1);
 }

#if defined(M63_RESOURCE_PROFILE)
 resource_status(OBSERVATION_SECONDS);
 puts("XCOVER5 M63 OBSERVATION_END:90 seconds; exit77 means capture complete ONLY; not UI readiness or lock-screen success");
#else
 puts("XCOVER5 M55 OBSERVATION_END:45 seconds; exit77 means capture complete ONLY; not UI readiness or lock-screen success");

#endif
 return 77;
}
