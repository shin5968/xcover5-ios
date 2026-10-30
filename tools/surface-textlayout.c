/* M54: native CoreText paragraph layout after M53 gates. */
#include "m53-baseline.c"
#include "panel-textlayout.h"
static int m54_run_scene(void) {
 alarm(30);if(m54_load_layout())fail(200,"m54_textlayout_load");
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer")),control=0;
 if(!svc || io.open(svc,mach_task_self(),0,&control) || !control)fail(198,"m54_control");
 uint64_t before[7]={0};persistent_status(control,before);if(before[1])fail(198,"m54_already_active");
 void *display=NULL;int rc=fb.open(svc,mach_task_self(),0,&display);io.release(svc);
 if(rc || !display || CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(198,"m54_open");
 Surface surfaces[2]={NULL,NULL};uint32_t ids[2]={0,0};
 for(unsigned slot=0;slot<2;slot++) {
  CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
  number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
  surfaces[slot]=api.IOSurfaceCreate(d);CFRelease(d);Surface s=surfaces[slot];
  if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 || api.IOSurfaceGetBytesPerRow(s)!=2880 ||
     api.IOSurfaceGetPixelFormat(s)!=0x42475241 || api.IOSurfaceGetAllocSize(s)<M48_BYTES)fail(198,"m54_surface");
  ids[slot]=api.IOSurfaceGetID(s);if(!ids[slot])fail(198,"m54_id");
 }
 if(ids[0]==ids[1])fail(198,"m54_distinct_buffers");
 puts("XCOVER5 M54 BEGIN:16 native CoreText wrapped paragraph frames; standard selectors4/5/6; two alternating surfaces");
 for(unsigned frame=0;frame<16;frame++) {
  Surface s=surfaces[frame&1];lock_surface(s,0,0);uint32_t *p=api.IOSurfaceGetBaseAddress(s);
  if(!p)fail(198,"m54_mapping");
  int draw=m54_draw(p,frame);if(draw){fprintf(stderr,"M54 draw rc=%d frame=%u\n",draw,frame+1);fail(200,"m54_textlayout_draw");}
  uint64_t hash=full_hash(p);lock_surface(s,0,1);
  uint32_t swap=0;if(fb.begin(display,&swap) || swap!=frame+1)fail(199,"m54_sequence");
  if(!fb.wait(display,swap,0))fail(199,"m54_premature_completion");
  FBRect rect={0,0,720,1480};
  if(fb.layer(display,0,s,rect,rect,0) || fb.end(display) || fb.wait(display,swap,0))fail(199,"m54_submit_wait");
  lock_surface(s,1,0);p=api.IOSurfaceGetBaseAddress(s);
  if(!p || full_hash(p)!=hash)fail(199,"m54_source_changed");lock_surface(s,1,1);
  if(frame>=2) {
   uint64_t state[7]={0};persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(199,"m54_not_persistent");
   usleep(350000);
   persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(199,"m54_not_held");
  }
 }
 uint32_t extra=0;if(!fb.begin(display,&extra))fail(199,"m54_frame_limit");
 CFRelease((CFTypeRef)display);display=NULL;
 uint64_t after[7]={0};unsigned tries;
 for(tries=0;tries<100;tries++) {persistent_status(control,after);if(after[0]!=before[0])break;usleep(50000);}
 if(tries==100 || after[0]!=before[0]+1 || after[1] || after[2]!=(uint32_t)getpid() || after[3]!=14 ||
    (after[4]!=1 && after[4]!=2) || after[5] || after[6]!=16)fail(199,"m54_close_restore");
 io.close(control);
 for(unsigned slot=0;slot<2;slot++)CFRelease(surfaces[slot]);
 for(unsigned slot=0;slot<2;slot++){Surface gone=api.IOSurfaceLookup(ids[slot]);if(gone){CFRelease(gone);fail(199,"m54_release");}}
 printf("XCOVER5 M54 PASS:16 composed frames/14 persistent copies; close restored=0 reason=%llu; both surfaces released\n",(unsigned long long)after[4]);
 return 76;
}
int main(int argc,char **argv) {
 int result=m53_baseline_main(argc,argv);if(argc!=1 || result!=75)return result;
 return m54_run_scene();
}
