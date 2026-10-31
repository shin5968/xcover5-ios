/* Adapt HackiOS init.c's RAMFS var policy to the existing XCover5 PID1 handoff.
 * Fresh data only; uses the already registered bounded32MiB RAMFS. No flash I/O. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#ifndef XC74_HOST_TEST
#include <sys/mount.h>
#endif
#define XC74_SEED "/usr/share/xcover5/m74-var-template"
struct xc74_entry {char kind;unsigned uid,gid,mode;char *path,*extra;};
static struct xc74_entry xc74_entries[512];
static char xc74_manifest[65536];
static unsigned xc74_count;
#ifdef XC74_HOST_TEST
static const char *xc74_prefix;
static int xc74_mount_var(void);
static int xc74_space(void);
#else
static const char *xc74_prefix="";
static int xc74_mount_var(void){return mount("ramfs","/private/var",0,NULL);}
static int xc74_space(void){
 struct statfs root,var;
 if(statfs("/",&root)||statfs("/private/var",&var))return -1;
 unsigned long long total=(unsigned long long)var.f_blocks*var.f_bsize,available=(unsigned long long)var.f_bavail*var.f_bsize;
 printf("XCOVER5 M74 VAR_SPACE type=%s total=%llu available=%llu root_available=%llu\n",var.f_fstypename,total,available,(unsigned long long)root.f_bavail*root.f_bsize);
 if(strcmp(var.f_fstypename,"ramfs")||total>32ULL*1024*1024||available<8ULL*1024*1024){errno=ENOSPC;return -1;}
 return 0;
}
#endif
static int xc74_path(char out[2048],const char *suffix){
 int n=snprintf(out,2048,"%s%s",xc74_prefix,suffix);
 if(n<0||n>=2048){errno=ENAMETOOLONG;return -1;}return 0;
}
static int xc74_number(const char *s,unsigned base,unsigned limit,unsigned *out){
 if(!*s||*s=='-'||*s=='+')return -1;
 char *end;errno=0;unsigned long n=strtoul(s,&end,base);
 if(errno||*end||n>limit)return -1;
 *out=(unsigned)n;return 0;
}
static int xc74_valid_path(const char *p){
 if(strcmp(p,"/private/var")&&strncmp(p,"/private/var/",13))return 0;
 if(strlen(p)>=1024||p[strlen(p)-1]=='/')return 0;
 for(const char *s=p+1;*s;){const char *e=strchr(s,'/');size_t n=e?(size_t)(e-s):strlen(s);
  if(!n||(n==1&&s[0]=='.')||(n==2&&s[0]=='.'&&s[1]=='.'))return 0;
  s=e?e+1:s+n;}
 return 1;
}
static int xc74_load(void){
 char path[2048];if(xc74_path(path,XC74_SEED "/manifest.tsv"))return -1;
 int fd=open(path,O_RDONLY|O_NOFOLLOW);if(fd<0)return -1;
 size_t used=0;ssize_t n;
 while((n=read(fd,xc74_manifest+used,sizeof(xc74_manifest)-1-used))>0){used+=(size_t)n;if(used==sizeof(xc74_manifest)-1)break;}
 char extra;int overflow=used==sizeof(xc74_manifest)-1&&read(fd,&extra,1)!=0;int saved=errno;close(fd);errno=saved;
 if(n<0||overflow||!used||xc74_manifest[used-1]!='\n'||memchr(xc74_manifest,0,used)){errno=EINVAL;return -1;}
 xc74_manifest[used]=0;xc74_count=0;unsigned long long total=0;
 char *cursor=xc74_manifest,*line;
 while((line=strsep(&cursor,"\n"))){
  if(!*line){if(cursor){errno=EINVAL;return -1;}break;}
  if(xc74_count==512){errno=E2BIG;return -1;}
  char *f[7],*rest=line;unsigned fields=0;
  while(fields<7&&(f[fields]=strsep(&rest,"\t")))fields++;
  if(fields<5||fields>6||strlen(f[0])!=1){errno=EINVAL;return -1;}
  struct xc74_entry *e=&xc74_entries[xc74_count];e->kind=f[0][0];e->path=f[4];e->extra=fields==6?f[5]:NULL;
  if(xc74_number(f[1],10,UINT32_MAX,&e->uid)||xc74_number(f[2],10,UINT32_MAX,&e->gid)||xc74_number(f[3],8,07777,&e->mode)||!xc74_valid_path(e->path)){errno=EINVAL;return -1;}
  if((e->kind=='d'&&fields!=5)||((e->kind=='f'||e->kind=='l')&&(fields!=6||!*e->extra))||(e->kind!='d'&&e->kind!='f'&&e->kind!='l')){errno=EINVAL;return -1;}
  for(unsigned i=0;i<xc74_count;i++)if(!strcmp(xc74_entries[i].path,e->path)){errno=EINVAL;return -1;}
  if(xc74_count==0){if(strcmp(e->path,"/private/var")||e->kind!='d'||e->uid||e->gid){errno=EINVAL;return -1;}}
  else {char parent[1024];strcpy(parent,e->path);*strrchr(parent,'/')=0;int found=0;
   for(unsigned i=0;i<xc74_count;i++)if(xc74_entries[i].kind=='d'&&!strcmp(xc74_entries[i].path,parent))found=1;
   if(!found){errno=EINVAL;return -1;}}
  if(e->kind=='f'){
   if(strlen(e->extra)!=8||strcmp(e->extra+4,".bin")){errno=EINVAL;return -1;}
   for(unsigned i=0;i<4;i++)if(e->extra[i]<'0'||e->extra[i]>'9'){errno=EINVAL;return -1;}
   char suffix[256];snprintf(suffix,sizeof(suffix),XC74_SEED "/files/%s",e->extra);
   if(xc74_path(path,suffix))return -1;
   struct stat st;if(lstat(path,&st)||!S_ISREG(st.st_mode)||st.st_size<0||st.st_size>1024*1024){errno=EINVAL;return -1;}
   total+=(unsigned long long)st.st_size;if(total>1024*1024){errno=E2BIG;return -1;}
  }
  if(e->kind=='l'&&strlen(e->extra)>=1024){errno=ENAMETOOLONG;return -1;}
  xc74_count++;
 }
 if(!xc74_count){errno=EINVAL;return -1;}
 return 0;
}
static int xc74_write_all(int fd,const void *data,size_t count){
 const char *p=data;while(count){ssize_t n=write(fd,p,count);if(n<0&&errno==EINTR)continue;if(n<=0){if(!n)errno=EIO;return -1;}p+=n;count-=(size_t)n;}return 0;
}
static int xc74_file(const struct xc74_entry *e,const char *dest){
 char suffix[256],source[2048],buf[4096];snprintf(suffix,sizeof(suffix),XC74_SEED "/files/%s",e->extra);
 if(xc74_path(source,suffix))return -1;
 int in=open(source,O_RDONLY|O_NOFOLLOW);if(in<0)return -1;
 int out=open(dest,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(out<0){int saved=errno;close(in);errno=saved;return -1;}
 ssize_t n;int result=0;
 while((n=read(in,buf,sizeof(buf)))!=0){if(n<0){if(errno==EINTR)continue;result=-1;break;}if(xc74_write_all(out,buf,(size_t)n)){result=-1;break;}}
 if(!result&&(fchown(out,e->uid,e->gid)||fchmod(out,e->mode)))result=-1;
 int saved=errno;if(close(out)&&!result){result=-1;saved=errno;}close(in);errno=saved;return result;
}
static int xc74_prepare(void){
 if(xc74_load()){printf("XCOVER5 M74 VAR_FAIL stage=manifest errno=%d\n",errno);return -1;}
 if(xc74_mount_var()){printf("XCOVER5 M74 VAR_FAIL stage=mount errno=%d\n",errno);return -1;}
 if(xc74_space())return -1;
 for(unsigned phase=0;phase<3;phase++)for(unsigned i=0;i<xc74_count;i++){
  struct xc74_entry *e=&xc74_entries[i];char path[2048];if(xc74_path(path,e->path))return -1;
  if(phase==0&&e->kind=='d'&&i&&mkdir(path,0700))return -1;
  if(phase==1&&e->kind=='f'&&xc74_file(e,path))return -1;
  if(phase==2&&e->kind=='l'&&(symlink(e->extra,path)||lchown(path,e->uid,e->gid)))return -1;
 }
 for(unsigned i=xc74_count;i>0;i--){struct xc74_entry *e=&xc74_entries[i-1];if(e->kind!='d')continue;
  char path[2048];if(xc74_path(path,e->path)||chown(path,e->uid,e->gid)||chmod(path,e->mode))return -1;
 }
 printf("XCOVER5 M74 VAR_READY records=%u; original owners/modes/seeds on fresh RAMFS\n",xc74_count);
 return xc74_space();
}
#ifndef XC74_HOST_TEST
static int xc74_mobile_proof(void){
 fflush(NULL);pid_t pid=fork();if(pid<0)return -1;
 if(!pid){
  if(setgid(501)||setuid(501))_exit(1);
  const char *path="/private/var/mobile/Library/FrontBoard/.m74-write-probe";
  int fd=open(path,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)_exit(2);
  char buf[4096],readback[4096];memset(buf,0x74,sizeof(buf));int ok=1;
  for(unsigned i=0;i<256&&ok;i++)if(xc74_write_all(fd,buf,sizeof(buf)))ok=0;
  if(ok&&(fsync(fd)||lseek(fd,0,SEEK_SET)!=0))ok=0;
  for(unsigned i=0;i<256&&ok;i++){ssize_t n=read(fd,readback,sizeof(readback));if(n!=(ssize_t)sizeof(readback)||memcmp(buf,readback,sizeof(buf)))ok=0;}
  if(close(fd)||unlink(path))ok=0;
  _exit(ok?0:3);
 }
 int status=0;pid_t done;do{done=waitpid(pid,&status,0);}while(done<0&&errno==EINTR);
 printf("XCOVER5 M74 MOBILE_IO pid=%d waited=%d status=%x bytes=1048576; actual RAMFS write/readback\n",pid,done,status);
 return done==pid&&WIFEXITED(status)&&WEXITSTATUS(status)==0?0:-1;
}
extern char **environ;
#if defined(M75_DIRECTORY_PROFILE)
#include "m75-dir-proof.h"
#endif
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
 printf("XCOVER5 M74 VAR_BEGIN pid=%d uid=%d; HackiOS RAMFS var policy before Apple launchd\n",getpid(),getuid());
 if(getpid()==1&&getuid()==0&&!xc74_prepare()&&!xc74_mobile_proof()
#if defined(M75_DIRECTORY_PROFILE)
  &&!xc75_dir_proof()
#endif
 ){
  char *argv[]={"/sbin/launchd.ios",NULL};
  printf("XCOVER5 M74 HANDOFF original Apple launchd, fresh writable var; no flash writes\n");
  execve(argv[0],argv,environ);
 }
 printf("XCOVER5 M74 HANDOFF_STOP errno=%d; PID1 stays alive, no success fabricated\n",errno);
 if(getpid()==1)for(;;)sleep(60);
 return 74;
}
#endif
