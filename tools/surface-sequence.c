/* M47: two bounded standard-framework sessions, alternating two real surfaces. */
#include "m46-baseline.c"
static int run_sequence(void) {
 alarm(30);
 for(unsigned round=0;round<2;round++) {
  mach_port_t service=io.service(0,io.matching("IOMobileFramebuffer"));
  if(!service)fail(244,"m47_service");
  void *display=NULL;int rc=fb.open(service,mach_task_self(),0,&display);io.release(service);
  if(rc || !display)fail(244,"m47_open");
  if(CFGetTypeID((CFTypeRef)display)!=fb.type_id())fail(244,"m47_type");
  Surface surfaces[2]={NULL,NULL};uint32_t ids[2]={0,0};
  for(unsigned slot=0;slot<2;slot++) {
   CFMutableDictionaryRef d=properties();surfaces[slot]=api.IOSurfaceCreate(d);CFRelease(d);
   if(!surfaces[slot])fail(245,"m47_create");
   ids[slot]=api.IOSurfaceGetID(surfaces[slot]);if(!ids[slot])fail(245,"m47_id");
  }
  if(ids[0]==ids[1])fail(245,"m47_distinct_buffers");
  printf("XCOVER5 M47 SESSION round=%u frames=16 sid=%u/%u\n",round,ids[0],ids[1]);
  for(unsigned frame=0;frame<16;frame++) {
   Surface s=surfaces[frame&1];lock_surface(s,0,0);volatile uint32_t *p=base(s);
   for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++) {
    unsigned column=(x+64-frame*4)%64;
    p[y*64+x]=column<8?(round?0xff00ff00U:0xffff0000U):(round?0xff202020U:0xff0000ffU);
   }
   uint64_t expected=hash_pixels((const uint32_t *)p);lock_surface(s,0,1);
   uint32_t swap=0;if(fb.begin(display,&swap) || swap!=frame+1)fail(246,"m47_sequence");
   FBRect src={0,0,64,32},dst={232,676,256,128};
   if(fb.layer(display,0,s,src,dst,0))fail(247,"m47_layer");
   if(fb.end(display))fail(248,"m47_end");
   if(fb.wait(display,swap,0))fail(249,"m47_wait");
   lock_surface(s,1,0);uint64_t actual=hash_pixels((const uint32_t *)base(s));lock_surface(s,1,1);
   if(actual!=expected)fail(250,"m47_source_changed");
   if((frame&3)==3)printf("XCOVER5 M47 FRAME round=%u completed=%u slot=%u hash=%llx\n",round,swap,frame&1,(unsigned long long)actual);
  }
  CFRelease((CFTypeRef)display);
  for(unsigned slot=0;slot<2;slot++)CFRelease(surfaces[slot]);
  for(unsigned slot=0;slot<2;slot++) {
   Surface gone=api.IOSurfaceLookup(ids[slot]);if(gone){CFRelease(gone);fail(251,"m47_release");}
  }
  printf("XCOVER5 M47 SESSION PASS round=%u frames=16 both_buffers_released\n",round);
 }
 puts("XCOVER5 M47 PASS: two sessions x16 standard submissions + alternating surfaces + completion + release");
 return 69;
}
int main(int argc,char **argv) {
 int result=m46_baseline_main(argc,argv);
 if(argc!=1 || result!=68)return result;
 return run_sequence();
}
