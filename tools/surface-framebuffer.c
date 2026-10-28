/* Generated m45-baseline.c differs from original only by renaming its final main. */
#include "m45-baseline.c"
typedef struct { double x,y,width,height; } FBRect;
typedef struct { double width,height; } FBSize;
static struct {
 int (*open)(mach_port_t,mach_port_t,uint32_t,void **);
 int (*size)(void *,FBSize *);
 int (*begin)(void *,uint32_t *);
 int (*layer)(void *,uint32_t,Surface,FBRect,FBRect,uint32_t);
 int (*end)(void *);
 int (*wait)(void *,uint32_t,uint32_t);
 CFTypeID (*type_id)(void);
} fb;
static void load_fb(void){
 void *h=dlopen("/System/Library/PrivateFrameworks/IOMobileFramebuffer.framework/IOMobileFramebuffer",RTLD_NOW|RTLD_LOCAL);
 if(!h){fprintf(stderr,"M46 framework dlopen: %s\n",dlerror());fail(234,"framebuffer_dlopen");}
#define FB_RESOLVE(member,name) do {dlerror();void *p=dlsym(h,name);const char *error=dlerror();if(error || !p){fprintf(stderr,"M46A RESOLVE failed symbol=%s error=%s\n",name,error?error:"null address");fail(235,name);}memcpy(&fb.member,&p,sizeof(p));printf("M46A RESOLVE PASS %s\n",name);}while(0)
 FB_RESOLVE(open,"IOMobileFramebufferOpen");FB_RESOLVE(size,"IOMobileFramebufferGetDisplaySize");
 FB_RESOLVE(begin,"IOMobileFramebufferSwapBegin");FB_RESOLVE(layer,"IOMobileFramebufferSwapSetLayer");
 FB_RESOLVE(end,"IOMobileFramebufferSwapEnd");FB_RESOLVE(wait,"IOMobileFramebufferSwapWait");
 /* iOS 16.5 exports no IOMobileFramebufferClose. Open creates a CFRuntime
  * instance whose registered finalizer closes the IOKit connection. */
 FB_RESOLVE(type_id,"IOMobileFramebufferGetTypeID");
#undef FB_RESOLVE
}
static void fb_result(int rc,const char *where){if(rc){fprintf(stderr,"M46 %s rc=%08x\n",where,(unsigned)rc);fail(236,where);}}
static int run_framebuffer(void){
 alarm(20);load_fb();
 mach_port_t service=io.service(0,io.matching("IOMobileFramebuffer"));
 if(!service)fail(237,"framebuffer_service");
 void *display=NULL;int rc=fb.open(service,mach_task_self(),0,&display);io.release(service);fb_result(rc,"Open");
 if(!display)fail(237,"null_display");
 if(CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(237,"framebuffer_CFTypeID");
 FBSize size={0};fb_result(fb.size(display,&size),"GetDisplaySize");
 if(size.width!=720 || size.height!=1480)fail(238,"display_geometry");
 if(!fb.wait(display,1,0))fail(239,"future_wait_accepted");
 CFMutableDictionaryRef d=properties();Surface s=api.IOSurfaceCreate(d);CFRelease(d);if(!s)fail(240,"create_surface");
 uint32_t sid=api.IOSurfaceGetID(s);
 FBRect src={0,0,64,32},dst={232,676,256,128};
 for(unsigned frame=0;frame<2;frame++){
  lock_surface(s,0,0);volatile uint32_t *pixels=base(s);
  for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++){
   pixels[y*64+x]=frame?(x<32?0xffff0000U:0xff0000ffU):(((x/8+y/8)&1)?0xffffffffU:0xff000000U);
  }
  uint64_t hash=hash_pixels((const uint32_t *)pixels);lock_surface(s,0,1);
  uint32_t swap=0;fb_result(fb.begin(display,&swap),"SwapBegin");if(swap!=frame+1)fail(241,"swap_sequence");
  printf("XCOVER5 M46 BEGIN frame=%u swap=%u hash=%llx pattern=%s\n",frame+1,swap,(unsigned long long)hash,frame?"RED_BLUE_HALVES":"CHECKERBOARD");
  fb_result(fb.layer(display,0,s,src,dst,0),"SwapSetLayer");
  fb_result(fb.end(display),"SwapEnd");
  fb_result(fb.wait(display,swap,0),"SwapWait");
  printf("XCOVER5 M46 FRAME PASS frame=%u standard_framework/end/wait\n",frame+1);
 }
 CFRelease((CFTypeRef)display);display=NULL;
 puts("M46A FRAMEBUFFER_RELEASE: CFRelease returned");
 CFRelease(s);
 Surface gone=api.IOSurfaceLookup(sid);if(gone){CFRelease(gone);fail(242,"surface_leak");}
 puts("XCOVER5 M46 PASS: real IOMobileFramebuffer Open/Size/Begin/SetLayer/End/Wait + CFRelease");
 return 68;
}
int main(int argc,char **argv){int result=m45_baseline_main(argc,argv);if(argc!=1 || result!=67)return result;return run_framebuffer();}
