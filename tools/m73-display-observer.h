/* Root-only readback of actual framebuffer state; one native touch wake test. */
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include "framebuffer/native_observation.h"
#include "compat/input.h"
struct m73_display {
 void *library;uint32_t connection;int tap_sent;
 int32_t(*call)(uint32_t,uint32_t,const uint64_t*,uint32_t,uint64_t*,uint32_t*);
 int32_t(*close)(uint32_t);
};
static struct m73_display m73;
static void m73_start(void){
 m73.library=dlopen("/System/Library/Frameworks/IOKit.framework/IOKit",RTLD_LAZY|RTLD_LOCAL);
 if(!m73.library)return;
 typedef CFMutableDictionaryRef(*match_fn)(const char*);
 typedef uint32_t(*find_fn)(uint32_t,CFDictionaryRef);
 typedef int32_t(*open_fn)(uint32_t,uint32_t,uint32_t,uint32_t*);
 typedef int32_t(*release_fn)(uint32_t);
 match_fn match=(match_fn)dlsym(m73.library,"IOServiceMatching");find_fn find=(find_fn)dlsym(m73.library,"IOServiceGetMatchingService");
 open_fn open_service=(open_fn)dlsym(m73.library,"IOServiceOpen");release_fn release=(release_fn)dlsym(m73.library,"IOObjectRelease");
 m73.call=(int32_t(*)(uint32_t,uint32_t,const uint64_t*,uint32_t,uint64_t*,uint32_t*))dlsym(m73.library,"IOConnectCallScalarMethod");
 m73.close=(int32_t(*)(uint32_t))dlsym(m73.library,"IOServiceClose");
 if(!match||!find||!open_service||!release||!m73.call||!m73.close)return;
 CFMutableDictionaryRef dict=match("IOMobileFramebuffer");uint32_t service=dict?find(0,dict):0;
 int32_t rc=service?open_service(service,mach_task_self(),0,&m73.connection):-1;
 if(rc)m73.connection=0;
 if(service)release(service);
 printf("XCOVER5 M73 DISPLAY_OBSERVER open=%x connection=%u\n",(unsigned)rc,m73.connection!=0);
 const char *resources[]={"/System/Library/Fonts/CoreUI/SFUI.ttf","/System/Library/CoreServices/SpringBoard.app/Assets.car",
  "/System/Library/PrivateFrameworks/CoreDuet.framework/_DKDataModel.momd/VersionInfo.plist",
  "/System/Library/PrivateFrameworks/CoreDuet.framework/_DKDataModel.momd/_DKDataModel35.mom",
  "/System/Library/PrivateFrameworks/CoreDuet.framework/_DKDataModel.momd/_DKDataModel35.omo"};
 for(unsigned i=0;i<sizeof(resources)/sizeof(resources[0]);i++){struct stat st;errno=0;int found=stat(resources[i],&st),error=errno;
  printf("XCOVER5 M73 RESOURCE path=%s stat=%d errno=%d bytes=%lld\n",resources[i],found,error,found?-1LL:(long long)st.st_size);}
 CFURLRef url=CFURLCreateWithFileSystemPath(kCFAllocatorDefault,CFSTR("/System/Library/PrivateFrameworks/CoreDuet.framework"),kCFURLPOSIXPathStyle,true);
 CFBundleRef bundle=url?CFBundleCreate(kCFAllocatorDefault,url):NULL;
 CFURLRef model=bundle?CFBundleCopyResourceURL(bundle,CFSTR("_DKDataModel"),CFSTR("momd"),NULL):NULL;
 printf("XCOVER5 M73 COREDUET bundle=%d model_url=%d; resource lookup only, not store initialization\n",bundle!=NULL,model!=NULL);
 if(model)CFRelease(model);
 if(bundle)CFRelease(bundle);
 if(url)CFRelease(url);
}
static void m73_observe(unsigned elapsed){
 if(!m73.connection||!m73.call)return;
 uint64_t command=1,out[XC73_DIAG_WORDS]={0};uint32_t count=XC73_DIAG_WORDS;
 int32_t rc=m73.call(m73.connection,XC73_DIAG_SELECTOR,&command,1,out,&count);
 printf("XCOVER5 M73 DISPLAY elapsed=%u rc=%x words=%u frames=%llu layers=%llx rgb=%llu empty=%llu black=%llu rejected=%llu last=%llx presented=%llu restored=%llu age_ms=%llu capture=%llu\n",
  elapsed,(unsigned)rc,count,out[1],out[2],out[3],out[4],out[5],out[6],out[7],out[8],out[9],out[10]/1000000,out[11]);
 if(rc||count!=XC73_DIAG_WORDS||out[0]!=XC73_DIAG_MAGIC)return;
 /* A single tap after a recovered blank frame. The existing HackiOS input bridge
  * maps it to a wake-button event only while TouchMode says the display is off.
  * No unlock notification, UI drawing or fabricated graphics completion. */
 if(!m73.tap_sent&&elapsed>=25&&out[1]&&out[3]==0&&out[9]){
  m73.tap_sent=1;errno=0;int fd=open(HAKIOS_TOUCH_DEVICE,O_WRONLY|O_NONBLOCK),error=errno;
  struct hakios_touch t={.time=0,.type=HAKIOS_TOUCH_DOWN,.finger=0,.x=32768,.y=32768};
  ssize_t down=fd<0?-1:write(fd,&t,sizeof(t));int down_error=errno;
  if(down==(ssize_t)sizeof(t))usleep(80000);
  t.type=HAKIOS_TOUCH_UP;ssize_t up=fd<0?-1:write(fd,&t,sizeof(t));int up_error=errno;
  if(fd>=0)close(fd);
  printf("XCOVER5 M73 WAKE_TAP open_errno=%d down=%ld errno=%d up=%ld errno=%d; native HID input test only\n",error,(long)down,down_error,(long)up,up_error);
 }
}
static void m73_finish(void){
 if(m73.connection&&m73.close)m73.close(m73.connection);
 if(m73.library)dlclose(m73.library);
}
