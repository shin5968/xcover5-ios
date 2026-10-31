/* Read actual data-volume space and DB files without manufacturing readiness. */
#include <sys/mount.h>
static void m74_var_status(unsigned elapsed){
 const char *mounts[]={"/","/private/var"};
 for(unsigned i=0;i<2;i++){struct statfs fs;errno=0;int rc=statfs(mounts[i],&fs),error=errno;
  printf("XCOVER5 M74 SPACE elapsed=%u path=%s rc=%d errno=%d type=%s total=%llu available=%llu\n",elapsed,mounts[i],rc,error,rc?"<none>":fs.f_fstypename,rc?0ULL:(unsigned long long)fs.f_blocks*fs.f_bsize,rc?0ULL:(unsigned long long)fs.f_bavail*fs.f_bsize);}
 const char *paths[]={"/private/var/mobile/Library/FrontBoard","/private/var/mobile/Library/FrontBoard/applicationState.db","/private/var/mobile/Library/FrontBoard/applicationState.db-wal","/private/var/mobile/Library/chronod/chrono.sql","/private/var/db/lsd"};
 for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);i++){struct stat st;errno=0;int rc=stat(paths[i],&st),error=errno;
  printf("XCOVER5 M74 DATA elapsed=%u path=%s rc=%d errno=%d uid=%u gid=%u mode=%o bytes=%lld\n",elapsed,paths[i],rc,error,rc?0U:st.st_uid,rc?0U:st.st_gid,rc?0U:st.st_mode&07777,rc?-1LL:(long long)st.st_size);}
}
