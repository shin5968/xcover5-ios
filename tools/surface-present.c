/* M45: diagnostic user-surface submission; preserves complete M43 source. */
#define main m43_baseline_main
#include "surface-sharing.c"
#undef main
#include <mach/mach.h>
static struct {
 CFMutableDictionaryRef (*matching)(const char *);
 mach_port_t (*service)(mach_port_t,CFDictionaryRef);
 int (*open)(mach_port_t,mach_port_t,uint32_t,mach_port_t *);
 int (*close)(mach_port_t);
 int (*release)(mach_port_t);
 int (*call)(mach_port_t,uint32_t,const uint64_t *,uint32_t,const void *,size_t,uint64_t *,uint32_t *,void *,size_t *);
} io;
static void load_io(void) {
 void *h=dlopen("/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit",RTLD_NOW|RTLD_LOCAL);
 if(!h)fail(220,"IOKit_dlopen");
#define IO_RESOLVE(member,symbol) do {void *p=dlsym(h,symbol);if(!p)fail(221,symbol);memcpy(&io.member,&p,sizeof(p));}while(0)
 IO_RESOLVE(matching,"IOServiceMatching");IO_RESOLVE(service,"IOServiceGetMatchingService");
 IO_RESOLVE(open,"IOServiceOpen");IO_RESOLVE(close,"IOServiceClose");IO_RESOLVE(release,"IOObjectRelease");
 IO_RESOLVE(call,"IOConnectCallMethod");
#undef IO_RESOLVE
}
static int submit(mach_port_t connection,uint32_t sid,uint64_t seq,uint64_t out[3]) {
 uint64_t in[2]={sid,seq};uint32_t n=3;
 int rc=io.call(connection,90,in,2,NULL,0,out,&n,NULL,NULL);
 if(!rc && n!=3)fail(222,"reply_count");
 return rc;
}
static uint64_t hash_pixels(const uint32_t *p) {
 uint64_t h=14695981039346656037ULL;const uint8_t *b=(const uint8_t *)p;
 for(unsigned i=0;i<8192;i++)h=(h^b[i])*1099511628211ULL;
 return h;
}
static int run_present(void) {
 alarm(20);load_io();
 CFMutableDictionaryRef d=properties();Surface s=api.IOSurfaceCreate(d);CFRelease(d);
 if(!s)fail(223,"create_user_surface");
 uint32_t sid=api.IOSurfaceGetID(s);if(!sid)fail(223,"surface_ID");
 mach_port_t service=io.service(0,io.matching("IOCoreSurfaceRoot")),connection=0;
 if(!service)fail(224,"surface_service");
 int rc=io.open(service,mach_task_self(),0,&connection);io.release(service);
 if(rc || !connection)fail(225,"open_connection");
 uint64_t out[3]={0};
 if(!submit(connection,sid,1,out))fail(226,"unowned_ID_accepted");
 uint64_t input=sid;uint8_t metadata[0xa68];size_t size=sizeof(metadata);
 rc=io.call(connection,4,&input,1,NULL,0,NULL,NULL,metadata,&size);
 if(rc || size<0x80)fail(227,"connection_lookup");
 if(!submit(connection,0,1,out))fail(228,"zero_ID_accepted");
 const uint32_t colors[8]={0xffff0000U,0xff00ff00U,0xff0000ffU,0xffffffffU,0xff00ffffU,0xffff00ffU,0xffffff00U,0xff000000U};
 for(unsigned frame=0;frame<2;frame++) {
  lock_surface(s,0,0);volatile uint32_t *pixels=base(s);
  for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++)pixels[y*64+x]=colors[frame?7-x/8:x/8];
  uint64_t expected=hash_pixels((const uint32_t *)pixels);lock_surface(s,0,1);
  printf("XCOVER5 M45 SUBMIT frame=%u id=%u hash=%llx order=%s\n",frame+1,sid,(unsigned long long)expected,frame?"REVERSED":"RGBWCMYK");
  if(submit(connection,sid,frame+1,out))fail(229,"submit");
  if(out[0]!=frame+1 || out[1]!=expected || out[2])fail(230,"completion_or_checksum");
  printf("XCOVER5 M45 FRAME PASS frame=%u checksum=matched console=restored\n",frame+1);
 }
 if(!submit(connection,sid,2,out))fail(231,"replay_accepted");
 if(io.close(connection))fail(232,"close_connection");
 CFRelease(s);
 Surface gone=api.IOSurfaceLookup(sid);if(gone){CFRelease(gone);fail(233,"surface_still_live");}
 puts("XCOVER5 M45 PASS: two user IOSurface submissions + checksum completion + console restore + release");
 return 67;
}
int main(int argc,char **argv) {
 int result=m43_baseline_main(argc,argv);
 if(argc!=1 || result!=64)return result;
 return run_present();
}

