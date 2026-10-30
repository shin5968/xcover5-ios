/* M49: standard full-panel IDs3..16 persist until real CFRelease closes display. */
#include "m48-baseline.c"
static void persistent_status(mach_port_t c,uint64_t out[7]) {
 uint32_t n=7;
 if(io.call(c,93,NULL,0,NULL,0,out,&n,NULL,NULL) || n!=7)fail(187,"m49_status");
}
static int run_persistent(void) {
 alarm(30);
 mach_port_t svc=io.service(0,io.matching("IOMobileFramebuffer")),control=0;
 if(!svc || io.open(svc,mach_task_self(),0,&control) || !control)fail(187,"m49_control");
 uint64_t before[7]={0};persistent_status(control,before);if(before[1])fail(187,"m49_already_active");
 void *display=NULL;int rc=fb.open(svc,mach_task_self(),0,&display);io.release(svc);
 if(rc || !display || CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(187,"m49_open");
 Surface surfaces[2]={NULL,NULL};uint32_t ids[2]={0,0};
 for(unsigned slot=0;slot<2;slot++) {
  CFMutableDictionaryRef d=properties();number(d,CFSTR("IOSurfaceWidth"),720);number(d,CFSTR("IOSurfaceHeight"),1480);
  number(d,CFSTR("IOSurfaceBytesPerRow"),2880);number(d,CFSTR("IOSurfaceAllocSize"),M48_BYTES);
  surfaces[slot]=api.IOSurfaceCreate(d);CFRelease(d);Surface s=surfaces[slot];
  if(!s || api.IOSurfaceGetWidth(s)!=720 || api.IOSurfaceGetHeight(s)!=1480 || api.IOSurfaceGetBytesPerRow(s)!=2880 ||
     api.IOSurfaceGetPixelFormat(s)!=0x42475241 || api.IOSurfaceGetAllocSize(s)<M48_BYTES)fail(188,"m49_surface");
  ids[slot]=api.IOSurfaceGetID(s);if(!ids[slot])fail(188,"m49_id");
 }
 if(ids[0]==ids[1])fail(188,"m49_distinct_buffers");
 puts("XCOVER5 M49 BEGIN:16 full-panel frames, IDs3..16 persistent, two alternating surfaces");
 for(unsigned frame=0;frame<16;frame++) {
  Surface s=surfaces[frame&1];lock_surface(s,0,0);uint32_t *p=api.IOSurfaceGetBaseAddress(s);
  if(!p)fail(188,"m49_mapping");
  for(unsigned y=0;y<1480;y++)for(unsigned x=0;x<720;x++) {
   unsigned column=(x+720-(frame*45)%720)%720;
   uint32_t color=column<90?(frame&1?0xff00ff00U:0xffff0000U):0xff000040U;
   if(x<4 || x>=716 || y<4 || y>=1476)color=0xffffffffU;
   p[y*720+x]=color;
  }
  uint64_t hash=full_hash(p);lock_surface(s,0,1);
  uint32_t swap=0;if(fb.begin(display,&swap) || swap!=frame+1)fail(189,"m49_sequence");
  if(!fb.wait(display,swap,0))fail(189,"m49_premature_completion");
  FBRect rect={0,0,720,1480};
  if(fb.layer(display,0,s,rect,rect,0) || fb.end(display) || fb.wait(display,swap,0))fail(189,"m49_submit_wait");
  lock_surface(s,1,0);p=api.IOSurfaceGetBaseAddress(s);
  if(!p || full_hash(p)!=hash)fail(189,"m49_source_changed");lock_surface(s,1,1);
  if(frame>=2) {
   uint64_t state[7]={0};persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(189,"m49_not_persistent");
   usleep(250000);
   persistent_status(control,state);
   if(state[0]!=before[0] || state[1]!=1)fail(189,"m49_not_held");
  }
 }
 uint32_t extra=0;if(!fb.begin(display,&extra))fail(189,"m49_frame_limit");
 CFRelease((CFTypeRef)display);display=NULL;
 uint64_t after[7]={0};unsigned tries;
 for(tries=0;tries<100;tries++) {persistent_status(control,after);if(after[0]!=before[0])break;usleep(50000);}
 if(tries==100 || after[0]!=before[0]+1 || after[1] || after[2]!=(uint32_t)getpid() || after[3]!=14 ||
    (after[4]!=1 && after[4]!=2) || after[5] || after[6]!=16)fail(189,"m49_close_restore");
 io.close(control);
 for(unsigned slot=0;slot<2;slot++)CFRelease(surfaces[slot]);
 for(unsigned slot=0;slot<2;slot++){Surface gone=api.IOSurfaceLookup(ids[slot]);if(gone){CFRelease(gone);fail(189,"m49_release");}}
 printf("XCOVER5 M49 PASS:16 full frames/14 persistent copies; close restored=0 reason=%llu; both surfaces released\n",(unsigned long long)after[4]);
 return 71;
}
int main(int argc,char **argv) {
 int result=m48_baseline_main(argc,argv);if(argc!=1 || result!=70)return result;
 return run_persistent();
}
