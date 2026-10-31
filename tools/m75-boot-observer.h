/* Re-read the current boot's actual preflight receipt after console recovery. */
static void m75_boot_status(unsigned elapsed){
 const char *path="/private/var/run/xcover-m75-boot-proof.txt";char proof[256]={0};errno=0;
 int fd=open(path,O_RDONLY|O_NOFOLLOW),error=errno;ssize_t n=fd<0?-1:read(fd,proof,sizeof(proof)-1);
 if(fd>=0){error=n<0?errno:0;close(fd);}
 if(n>0&&proof[n-1]=='\n')proof[n-1]=0;
 printf("XCOVER5 M75 PREFLIGHT elapsed=%u read=%ld errno=%d receipt=%s\n",elapsed,(long)n,error,n>0?proof:"<unavailable>");
}
