/* Native libc fdopendir/readdir must work on RAMFS before Apple daemons start. */
#include <dirent.h>
#include <grp.h>
static int xc75_directory(const char *path){
 int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);if(fd<0){printf("XCOVER5 M75 DIR_IO path=%s uid=%d open_errno=%d\n",path,getuid(),errno);return -1;}
 errno=0;DIR *directory=fdopendir(fd);int error=errno;
 if(!directory){close(fd);printf("XCOVER5 M75 DIR_IO path=%s uid=%d fdopendir=NULL errno=%d\n",path,getuid(),error);return -1;}
 unsigned count=0;errno=0;struct dirent *entry;
 while((entry=readdir(directory))){if(!entry->d_name[0]||++count>1024){error=EIO;break;}}
 if(!error)error=errno;
 if(closedir(directory)&&!error)error=errno;
 printf("XCOVER5 M75 DIR_IO path=%s uid=%d entries=%u errno=%d; actual libc directory enumeration\n",path,getuid(),count,error);
 return !error&&count>=2?0:-1;
}
static int xc75_dir_proof(void){
 const char *names[]={"/private/var/db/diagnostics","/private/var/mobile/Library/FrontBoard"};
 const unsigned identities[]={272,501};int statuses[2]={-1,-1};
 for(unsigned i=0;i<2;i++){
  char path[2048];if(xc74_path(path,names[i]))return -1;
  fflush(NULL);pid_t pid=fork();if(pid<0)return -1;
  if(!pid){if(setgroups(0,NULL)||setgid(identities[i])||setuid(identities[i]))_exit(1);int rc=xc75_directory(path);fflush(NULL);_exit(rc?2:0);}
  pid_t done;do{done=waitpid(pid,&statuses[i],0);}while(done<0&&errno==EINTR);
  printf("XCOVER5 M75 DIR_WAIT uid=%u pid=%d waited=%d status=%x\n",identities[i],pid,done,statuses[i]);
  if(done!=pid||!WIFEXITED(statuses[i])||WEXITSTATUS(statuses[i]))return -1;
 }
 char path[2048],proof[256];if(xc74_path(path,"/private/var/run/xcover-m75-boot-proof.txt"))return -1;
 int n=snprintf(proof,sizeof(proof),"XCOVER5 M75 BOOT_PROOF records=%u mobile_io=PASS logd_dir_status=%x mobile_dir_status=%x\n",xc74_count,statuses[0],statuses[1]);
 if(n<0||n>=(int)sizeof(proof))return -1;
 int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)return -1;
 int rc=xc74_write_all(fd,proof,(size_t)n);if(!rc&&fchmod(fd,0644))rc=-1;if(close(fd))rc=-1;
 if(!rc)printf("%s",proof);
 return rc;
}
