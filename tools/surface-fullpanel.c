/* M48 exact physical-panel geometry; retains original M47 baseline. */
#include "m47-baseline.c"
#define M48_BYTES (720U*1480U*4U)
static uint64_t full_hash(const uint32_t *p) {
 uint64_t h=14695981039346656037ULL;const uint8_t *b=(const uint8_t *)p;
 for(unsigned i=0;i<M48_BYTES;i++)h=(h^b[i])*1099511628211ULL;
 return h;
}
static int run_fullpanel(void) {
 alarm(30);
 mach_port_t service=io.service(0,io.matching("IOMobileFramebuffer"));
 if(!service)fail(252,"m48_service");
 void *display=NULL;int rc=fb.open(service,mach_task_self(),0,&display);io.release(service);
 if(rc || !display || CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(252,"m48_open");
 FBSize size={0};if(fb.size(display,&size) || size.width!=720 || size.height!=1480)fail(252,"m48_geometry");
 CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
 number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
 Surface s=api.IOSurfaceCreate(d);CFRelease(d);
 if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 ||
    api.IOSurfaceGetBytesPerRow(s)!=2880 || api.IOSurfaceGetPixelFormat(s)!=0x42475241 ||
    api.IOSurfaceGetAllocSize(s)<M48_BYTES || api.IOSurfaceGetAllocSize(s)>(8U<<20))fail(253,"m48_surface_shape");
 uint32_t sid=api.IOSurfaceGetID(s);if(!sid)fail(253,"m48_surface_id");
 const uint32_t colors[8]={0xffff0000U,0xff00ff00U,0xff0000ffU,0xffffffffU,0xff00ffffU,0xffff00ffU,0xffffff00U,0xff000000U};
 for(unsigned frame=0;frame<2;frame++) {
  lock_surface(s,0,0);uint32_t *p=api.IOSurfaceGetBaseAddress(s);if(!p)fail(253,"m48_mapping");
  for(unsigned y=0;y<1480;y++)for(unsigned x=0;x<720;x++) {
   uint32_t pixel=frame?(((x/90+y/185)&1)?0xffffffffU:0xff000000U):colors[x/90];
   if(x<4 || x>=716 || y<4 || y>=1476)pixel=0xffffffffU;
   p[y*720+x]=pixel;
  }
  uint64_t expected=full_hash(p);lock_surface(s,0,1);
  uint32_t swap=0;if(fb.begin(display,&swap) || swap!=frame+1)fail(254,"m48_sequence");
  FBRect rect={0,0,720,1480};
  printf("XCOVER5 M48 BEGIN frame=%u sid=%u bytes=%u hash=%llx pattern=%s\n",frame+1,sid,M48_BYTES,(unsigned long long)expected,frame?"FULL_CHECKERBOARD":"FULL_COLOR_BARS");
  if(fb.layer(display,0,s,rect,rect,0))fail(254,"m48_layer");
  if(fb.end(display))fail(254,"m48_end");
  if(fb.wait(display,swap,0))fail(254,"m48_wait");
  lock_surface(s,1,0);p=api.IOSurfaceGetBaseAddress(s);if(!p || full_hash(p)!=expected)fail(254,"m48_source_changed");lock_surface(s,1,1);
  printf("XCOVER5 M48 FRAME PASS id=%u source_unchanged\n",swap);
 }
 CFRelease((CFTypeRef)display);CFRelease(s);
 Surface gone=api.IOSurfaceLookup(sid);if(gone){CFRelease(gone);fail(255,"m48_release");}
 puts("XCOVER5 M48 PASS: full720x1480 standard submissions + source integrity + console restore + release");
 return 70;
}
int main(int argc,char **argv) {
 int result=m47_baseline_main(argc,argv);if(argc!=1 || result!=69)return result;
 return run_fullpanel();
}
