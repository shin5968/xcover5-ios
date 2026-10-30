/* M52: native Apple CoreGraphics bitmap drawing after all M51 gates. */
#include "m51-baseline.c"
#include "panel-coregraphics.h"
static int m52_run_scene(void) {
 alarm(30);if(m52_load_cg())fail(194,"m52_coregraphics_load");
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer")),control=0;
 if(!svc || io.open(svc,mach_task_self(),0,&control) || !control)fail(192,"m52_control");
 uint64_t before[7]={0};persistent_status(control,before);if(before[1])fail(192,"m52_already_active");
 void *display=NULL;int rc=fb.open(svc,mach_task_self(),0,&display);io.release(svc);
 if(rc || !display || CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(192,"m52_open");
 Surface surfaces[2]={NULL,NULL};uint32_t ids[2]={0,0};
 for(unsigned slot=0;slot<2;slot++) {
  CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
  number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
  surfaces[slot]=api.IOSurfaceCreate(d);CFRelease(d);Surface s=surfaces[slot];
  if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 || api.IOSurfaceGetBytesPerRow(s)!=2880 ||
     api.IOSurfaceGetPixelFormat(s)!=0x42475241 || api.IOSurfaceGetAllocSize(s)<M48_BYTES)fail(192,"m52_surface");
  ids[slot]=api.IOSurfaceGetID(s);if(!ids[slot])fail(192,"m52_id");
 }
 if(ids[0]==ids[1])fail(192,"m52_distinct_buffers");
 puts("XCOVER5 M52 BEGIN:16 Apple CoreGraphics bitmap frames; standard selectors4/5/6; two alternating surfaces");
 for(unsigned frame=0;frame<16;frame++) {
  Surface s=surfaces[frame&1];lock_surface(s,0,0);uint32_t *p=api.IOSurfaceGetBaseAddress(s);
  if(!p)fail(192,"m52_mapping");
  int draw=m52_draw(p,frame);if(draw){fprintf(stderr,"M52 draw rc=%d frame=%u\n",draw,frame+1);fail(194,"m52_coregraphics_draw");}
  uint64_t hash=full_hash(p);lock_surface(s,0,1);
  uint32_t swap=0;if(fb.begin(display,&swap) || swap!=frame+1)fail(193,"m52_sequence");
  if(!fb.wait(display,swap,0))fail(193,"m52_premature_completion");
  FBRect rect={0,0,720,1480};
  if(fb.layer(display,0,s,rect,rect,0) || fb.end(display) || fb.wait(display,swap,0))fail(193,"m52_submit_wait");
  lock_surface(s,1,0);p=api.IOSurfaceGetBaseAddress(s);
  if(!p || full_hash(p)!=hash)fail(193,"m52_source_changed");lock_surface(s,1,1);
  if(frame>=2) {
   uint64_t state[7]={0};persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(193,"m52_not_persistent");
   usleep(350000);
   persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(193,"m52_not_held");
  }
 }
 uint32_t extra=0;if(!fb.begin(display,&extra))fail(193,"m52_frame_limit");
 CFRelease((CFTypeRef)display);display=NULL;
 uint64_t after[7]={0};unsigned tries;
 for(tries=0;tries<100;tries++) {persistent_status(control,after);if(after[0]!=before[0])break;usleep(50000);}
 if(tries==100 || after[0]!=before[0]+1 || after[1] || after[2]!=(uint32_t)getpid() || after[3]!=14 ||
    (after[4]!=1 && after[4]!=2) || after[5] || after[6]!=16)fail(193,"m52_close_restore");
 io.close(control);
 for(unsigned slot=0;slot<2;slot++)CFRelease(surfaces[slot]);
 for(unsigned slot=0;slot<2;slot++){Surface gone=api.IOSurfaceLookup(ids[slot]);if(gone){CFRelease(gone);fail(193,"m52_release");}}
 printf("XCOVER5 M52 PASS:16 composed frames/14 persistent copies; close restored=0 reason=%llu; both surfaces released\n",(unsigned long long)after[4]);
 return 74;
}
int main(int argc,char **argv) {
 int result=m51_baseline_main(argc,argv);if(argc!=1 || result!=73)return result;
 return m52_run_scene();
}
