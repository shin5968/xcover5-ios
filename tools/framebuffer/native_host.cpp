// Owned host harness: actual M68 service/selector/compositor bodies, mocked IOKit/panel.
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <map>
#include <vector>
#include <string>
#define XC68_HOST_TEST 1
#define APPLE_KEXT_OVERRIDE override
#define OSDeclareDefaultStructors(C) public: C()=default; virtual ~C()=default;
#define OSDefineMetaClassAndStructors(C,B)
#define OSTypeAlloc(C) new C
#define OSDynamicCast(C,o) dynamic_cast<C*>(o)
#define OSSafeReleaseNULL(o) do{if(o){(o)->release();(o)=nullptr;}}while(0)
#define task_t MockTask
#define mach_port_t MockPort
using UInt32=uint32_t;using task_t=void*;using mach_port_t=void*;
using mach_port_name_t=uint32_t;using io_user_reference_t=uint64_t;
using thread_call_param_t=void*;using OSAsyncReference64=uint64_t[8];
enum {kIOReturnSuccess=0,kIOReturnBadArgument=2,kIOReturnNoMemory=3,kIOReturnError=4,
 kIOReturnNotReady=5,kIOReturnNotOpen=6,kIOReturnUnsupported=7,kIOReturnNotPrivileged=8,kIOReturnBusy=9,kIOUserNotifyOptionCanDrop=1};
using IOReturn=int;struct IOExternalMethodDispatch{};
struct IOExternalMethodArguments{uint64_t *scalarInput=nullptr,*scalarOutput=nullptr;
 uint32_t scalarInputCount=0,scalarOutputCount=0;void *structureInput=nullptr,*structureOutput=nullptr;
 uint32_t structureInputSize=0,structureOutputSize=0;void *structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;};
static void logmsg(const char *fmt,...){(void)fmt;}
#define IOLog(...) logmsg(__VA_ARGS__)
static unsigned actor_uid=501;static void*current_proc_EXTERNAL(){return nullptr;}
static unsigned proc_getuid(void*){return actor_uid;}static int proc_selfpid(){return 42;}
struct OSObject{int refs=1;virtual ~OSObject()=default;virtual void free(){};void retain(){refs++;}void release(){assert(refs>0);if(!--refs){free();delete this;}}};
struct OSNumber:OSObject{uint32_t value;static OSNumber*withNumber(uint32_t v,int){auto*n=new OSNumber;n->value=v;return n;}};
struct OSBoolean:OSObject{bool value=false;};static OSBoolean false_obj;static OSBoolean*kOSBooleanFalse=&false_obj;
struct OSData:OSObject{std::vector<uint8_t>data;};
struct OSDictionary:OSObject{std::map<std::string,OSObject*>map;
 static OSDictionary*withCapacity(int){return new OSDictionary;}
 void setObject(const char*k,OSObject*v){v->retain();auto it=map.find(k);if(it!=map.end())it->second->release();map[k]=v;}
 OSObject*getObject(const char*k){auto it=map.find(k);return it==map.end()?nullptr:it->second;}
 ~OSDictionary(){for(auto&i:map)i.second->release();}};
struct OSArray:OSObject{std::vector<OSObject*>array;static OSArray*withCapacity(int){return new OSArray;}
 void setObject(OSObject*v){v->retain();array.push_back(v);}~OSArray(){for(auto*v:array)v->release();}};
struct IORegistryEntry:OSObject{OSDictionary*properties=new OSDictionary;
 virtual ~IORegistryEntry(){properties->release();}
 void setProperty(const char*k,OSObject*v){properties->setObject(k,v);}
 void setProperty(const char*k,const char*){auto*d=new OSData;properties->setObject(k,d);d->release();}
 void setProperty(const char*k,const void*p,size_t n){auto*d=new OSData;d->data.assign((const uint8_t*)p,(const uint8_t*)p+n);properties->setObject(k,d);d->release();}
 OSObject*getProperty(const char*k){return properties->getObject(k);}
 static IORegistryEntry*fromPath(const char*,void*);};
static IORegistryEntry*chosen=new IORegistryEntry,*product=new IORegistryEntry;static void*gIODTPlane=nullptr;
IORegistryEntry*IORegistryEntry::fromPath(const char*s,void*){auto*n=!strcmp(s,"/chosen")?chosen:product;n->retain();return n;}
static const char*kIOUserClientClassKey="IOUserClientClass";
struct IOService:IORegistryEntry{bool inactive=false;std::string name;
 virtual bool init(OSDictionary* =nullptr){return true;}virtual bool start(IOService*){return true;}
 bool attach(IOService*){return true;}void detach(IOService*){}void registerService(){}void setName(const char*s){name=s;}
 bool isInactive(){return inactive;}void terminate(){inactive=true;}void free()override{}};
struct IOLock{bool held=false;};static int live_locks=0;static bool busy_lock=false;
static IOLock*IOLockAlloc(){live_locks++;return new IOLock;}
static bool IOLockTryLock(IOLock*l){if(busy_lock||l->held)return false;l->held=true;return true;}
static void IOLockLock(IOLock*l){assert(l&&!l->held);l->held=true;}
static void IOLockUnlock(IOLock*l){assert(l&&l->held);l->held=false;}
static void IOLockFree(IOLock*l){assert(l&&!l->held);live_locks--;delete l;}
struct ThreadCall{void(*fn)(void*,void*);void*self;bool armed=false;};using thread_call_t=ThreadCall*;
static ThreadCall*last_call=nullptr;static unsigned live_calls=0,notifications=0,ports_released=0;
static thread_call_t thread_call_allocate(void(*fn)(void*,void*),void*self){live_calls++;last_call=new ThreadCall{fn,self};return last_call;}
static void thread_call_enter_delayed(thread_call_t c,uint64_t){c->armed=true;}
static void thread_call_cancel_wait(thread_call_t c){c->armed=false;}
static void thread_call_free(thread_call_t c){assert(!c->armed);live_calls--;delete c;}
#define NSEC_PER_SEC 1000000000ULL
static uint64_t fake_now=123456789;static uint64_t mach_absolute_time(){return fake_now;}
static void absolutetime_to_nanoseconds(uint64_t n,uint64_t*p){*p=n;}
static void nanoseconds_to_absolutetime(uint64_t n,uint64_t*p){*p=n;}
struct IOUserClient:IOService{
 virtual bool initWithTask(task_t,void*,UInt32,OSDictionary*){return true;}
 virtual IOReturn registerNotificationPort(mach_port_t,UInt32,io_user_reference_t){return 0;}
 virtual IOReturn clientClose(){return 0;}
 virtual IOReturn externalMethod(uint32_t,IOExternalMethodArguments*,IOExternalMethodDispatch*,OSObject*,void*){return 0;}
 void releaseNotificationPort(mach_port_t){ports_released++;}
 void setAsyncReference64(OSAsyncReference64 r,mach_port_t,io_user_reference_t cb,io_user_reference_t ctx,task_t){r[0]=cb;r[1]=ctx;}
 void sendAsyncResult64WithOptions(OSAsyncReference64 r,int result,io_user_reference_t*a,int n,int){assert(r[0]&&result==0&&n==6&&a[4]);notifications++;}
};
static unsigned alloc_calls=0,alloc_fail_at=0;static int live_allocations=0;static void*IOMalloc(size_t n){if(++alloc_calls==alloc_fail_at)return nullptr;void*p=malloc(n);if(p)live_allocations++;return p;}
static void IOFree(void*p,size_t){assert(p);live_allocations--;free(p);}
struct MiniIOSurface{struct{uint32_t width,height,bytesPerRow,bytesPerElement,pixelFormat,planeCount;uint64_t allocSize;}info;
 uint8_t*kpixels;void*client=nullptr;unsigned refs=1,id;};
static MiniIOSurface*surfaces[256];static unsigned live_surfaces=0;
static MiniIOSurface*MiniIOSurfaceCreateSimple(uint32_t w,uint32_t h,uint32_t format){
 auto*s=new MiniIOSurface;s->info={w,h,(w*4+63)&~63U,4,format,0,0};s->info.allocSize=(uint64_t)s->info.bytesPerRow*h;
 assert(s->info.allocSize<=(8U<<20));s->kpixels=(uint8_t*)calloc(1,s->info.allocSize);
 for(unsigned id=1;id<256;id++)if(!surfaces[id]){s->id=id;surfaces[id]=s;live_surfaces++;return s;}abort();}
static MiniIOSurface*MiniIOSurfaceCopy(uint32_t id){if(id>=256||!surfaces[id])return nullptr;surfaces[id]->refs++;return surfaces[id];}
static void MiniIOSurfaceDrop(MiniIOSurface*s){assert(s->refs);if(!--s->refs){surfaces[s->id]=nullptr;free(s->kpixels);delete s;live_surfaces--;}}
static mach_port_name_t MiniIOSurfaceMakeSendRight(task_t,MiniIOSurface*s){return s->id+100;}
static std::vector<uint32_t>panel(720*1480+2,0xabcdef01);static bool presenting=false;
static bool fail_begin=false,fail_update=false;static unsigned begins=0,updates=0,restores=0;
static int xcover5_full_present_begin(const uint32_t*p,uint32_t*s){if(fail_begin)return 1;assert(!presenting);memcpy(s,panel.data()+1,720*1480*4);memcpy(panel.data()+1,p,720*1480*4);presenting=true;begins++;return 0;}
static int xcover5_full_present_update(const uint32_t*p){assert(presenting);if(fail_update)return 1;memcpy(panel.data()+1,p,720*1480*4);updates++;return 0;}
static int xcover5_full_present_end(const uint32_t*s){assert(presenting);memcpy(panel.data()+1,s,720*1480*4);presenting=false;restores++;return 0;}
#include "XCoverNativeFramebuffer.h"
static uint32_t number(OSDictionary*d,const char*k){auto*n=dynamic_cast<OSNumber*>(d->getObject(k));assert(n);return n->value;}
static IOReturn call(IOMobileFramebufferUserClient*c,unsigned sel,IOExternalMethodArguments&a){return c->externalMethod(sel,&a,nullptr,nullptr,nullptr);}
static void m73_test();
int main(){
 auto*fb=new IOMobileFramebuffer;assert(fb->init()&&fb->start(nullptr));
 auto*timings=dynamic_cast<OSArray*>(fb->getProperty("TimingElements"));assert(timings&&timings->array.size()==1);
 auto*t=dynamic_cast<OSDictionary*>(timings->array[0]);assert(t&&number(t,"ID")==1);
 auto*h=dynamic_cast<OSDictionary*>(t->getObject("HorizontalAttributes"));auto*v=dynamic_cast<OSDictionary*>(t->getObject("VerticalAttributes"));
 assert(number(h,"Active")==750&&number(v,"Active")==1624&&number(v,"SyncRate")==60U<<16);
 auto*colors=dynamic_cast<OSArray*>(fb->getProperty("ColorElements"));assert(colors&&colors->array.size()==1);
 assert(number(dynamic_cast<OSDictionary*>(colors->array[0]),"ID")==1);
 assert(dynamic_cast<OSBoolean*>(t->getObject("IsVirtual"))->value==false);
 for(auto pair: {std::pair<IORegistryEntry*,const char*>(chosen,"display-scale"),{product,"artwork-scale-factor"}}){auto*d=dynamic_cast<OSData*>(pair.first->getProperty(pair.second));assert(d&&d->data.size()==4&&d->data[0]==2);}
 auto*c=new IOMobileFramebufferUserClient;assert(c->initWithTask((void*)1,nullptr,0,nullptr)&&c->start(fb));
 uint64_t input[8]={0},output[8]={0};IOExternalMethodArguments a;a.scalarInput=input;a.scalarOutput=output;
 a.scalarOutputCount=2;assert(!call(c,8,a)&&output[0]==750&&output[1]==1624);
 a.scalarOutputCount=1;assert(!call(c,28,a)&&output[0]==305);
 assert(!call(c,7,a)&&output[0]==1);assert(!call(c,77,a)&&output[0]==mach_absolute_time());
 a.scalarOutputCount=0;assert(call(c,8,a)==kIOReturnBadArgument);assert(!call(c,95,a)&&!presenting);
 // BackBoard's bootstrap Wait(0,0x80000003,0) succeeds without presenting a frame.
 a.scalarInputCount=3;input[0]=0;input[1]=0x80000003;input[2]=0;
 assert(!call(c,6,a)&&!presenting&&begins==0);a.scalarInputCount=0;
 a.scalarOutputCount=1;output[0]=~0ULL;assert(!call(c,25,a)&&output[0]==0);assert(!call(c,3,a)&&output[0]>100);unsigned sid=(unsigned)output[0]-100;
 auto*s=surfaces[sid];assert(s&&s->info.width==750&&s->info.height==1624);
 for(uint32_t y=0;y<1624;y++){auto*row=(uint32_t*)(s->kpixels+y*s->info.bytesPerRow);for(uint32_t x=0;x<750;x++)row[x]=0xff000000U|(y<<12)|x;}
 uint8_t block[16];memset(block,0xee,sizeof(block));a.scalarInputCount=1;input[0]=0x40;a.structureOutput=block;a.structureOutputSize=16;
 assert(!call(c,79,a)&&xc68word(block,0)==0&&xc68word(block,4)==1&&xc68word(block,8)==1&&xc68word(block,12)==0);
 a.structureOutput=nullptr;a.structureOutputSize=0;a.scalarInputCount=0;a.scalarOutputCount=1;
 assert(!call(c,4,a));uint32_t id=(uint32_t)output[0];assert(id);
 uint8_t swap[0x46c]={0};auto put=[&](unsigned off,uint32_t value){memcpy(swap+off,&value,4);};
 put(0x50,id);put(0x54,sid);put(0x6c,750);put(0x70,1624);put(0xcc,750);put(0xd0,1624);put(0x104,1);
 a.scalarOutputCount=0;a.scalarInputCount=1;input[0]=0;assert(call(c,6,a)==kIOReturnNotReady);
 input[0]=id;assert(call(c,6,a)==kIOReturnNotReady);
 a.scalarInputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);
 alloc_fail_at=alloc_calls+2;assert(call(c,5,a)==kIOReturnNoMemory&&!presenting&&live_allocations==0);alloc_fail_at=0;
 put(0x6c,751);assert(call(c,5,a)==kIOReturnBadArgument&&!presenting);put(0x6c,750);
 fail_begin=true;assert(call(c,5,a)==kIOReturnError&&!presenting);fail_begin=false;
 assert(!call(c,5,a)&&presenting&&begins==1);
 assert(panel.front()==0xabcdef01&&panel.back()==0xabcdef01&&panel[1]==0xff000000);
 assert(panel[720*1480]==(0xff000000U|(1622U<<12)|748));
 a.structureInput=nullptr;a.structureInputSize=0;a.scalarInputCount=1;assert(!call(c,6,a));input[0]=id+100;assert(call(c,6,a)==kIOReturnNotReady);
 // Completion does not advance when the actual panel update fails.
 a.scalarInputCount=0;a.scalarOutputCount=1;assert(!call(c,4,a));id=(uint32_t)output[0];put(0x50,id);
 a.scalarOutputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);fail_update=true;assert(call(c,5,a)==kIOReturnError);fail_update=false;
 a.structureInput=nullptr;a.structureInputSize=0;a.scalarInputCount=1;input[0]=0;assert(call(c,6,a)==kIOReturnNotReady);
 input[0]=id;assert(call(c,6,a)==kIOReturnNotReady);
 a.scalarInputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);assert(!call(c,5,a)&&updates==1);
 // A malformed later layer may not partially overwrite the panel.
 a.structureInput=nullptr;a.structureInputSize=0;a.scalarOutputCount=1;assert(!call(c,4,a));put(0x50,(uint32_t)output[0]);
 a.scalarOutputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);
 std::vector<uint32_t>before=panel;put(0x58,255);assert(call(c,5,a)==kIOReturnBadArgument&&panel==before);put(0x58,0);
 // Notification ABI: retained port, callback/refcon/type and six32-bit halves.
 assert(!c->registerNotificationPort((void*)2,5,0));assert(c->registerNotificationPort((void*)2,8,0)==kIOReturnBadArgument);
 a.structureInput=nullptr;a.structureInputSize=0;a.scalarInputCount=3;input[0]=0x123;input[1]=0x456;input[2]=5;
 assert(!call(c,72,a)&&last_call->armed);last_call->fn(last_call->self,nullptr);assert(notifications==1&&last_call->armed);
 assert(!c->clientClose()&&!presenting&&restores==1&&!last_call->armed);assert(panel==std::vector<uint32_t>(panel.size(),0xabcdef01));c->release();
 assert(ports_released==1&&live_calls==0);fb->release();m73_test();chosen->release();product->release();
 assert(live_surfaces==0&&live_allocations==0&&live_locks==0);
 puts("M68 actual native service: mobile client admission, modes/current IDs/DPI/default surface, guarded scaling/panel canaries, failed completion, timed notification and close cleanup PASS");
}
static void m73_test(){
 auto*fb=new IOMobileFramebuffer;assert(fb->init()&&fb->start(nullptr));
 auto*c=new IOMobileFramebufferUserClient;assert(c->initWithTask((void*)1,nullptr,0,nullptr)&&c->start(fb));
 uint64_t in[3]={0},out[13]={0};out[12]=0xfeedface;
 IOExternalMethodArguments a;a.scalarInput=in;a.scalarOutput=out;
 auto query=[&](unsigned command){a.structureInput=nullptr;a.structureInputSize=0;a.scalarInputCount=1;in[0]=command;a.scalarOutputCount=12;return call(c,XC73_DIAG_SELECTOR,a);};
 actor_uid=501;assert(query(0)==kIOReturnNotPrivileged);actor_uid=0;
 assert(!query(0)&&out[0]==XC73_DIAG_MAGIC&&!out[1]&&!out[8]&&out[12]==0xfeedface);
 a.scalarOutputCount=11;assert(call(c,XC73_DIAG_SELECTOR,a)==kIOReturnBadArgument);
 assert(query(2)==kIOReturnBadArgument);busy_lock=true;assert(query(0)==kIOReturnBusy);busy_lock=false;
 uint8_t swap[0x46c]={0};auto put=[&](unsigned at,uint32_t v){memcpy(swap+at,&v,4);};
 auto submit=[&](){a.scalarInputCount=0;a.structureInput=nullptr;a.structureInputSize=0;a.scalarOutputCount=1;assert(!call(c,4,a));put(0x50,(uint32_t)out[0]);a.scalarOutputCount=0;a.structureInput=swap;a.structureInputSize=sizeof(swap);return call(c,5,a);};
 auto before=panel;unsigned old_restores=restores;
 assert(!submit()&&presenting);assert(!query(0)&&out[1]==1&&out[2]==0&&out[3]==0&&out[4]==1&&out[5]==1);
 fake_now+=1000000000ULL;assert(!query(1)&&presenting&&restores==old_restores);
 fake_now+=2000000000ULL;assert(!query(1)&&!presenting&&panel==before&&out[9]==1&&out[11]==1);
 // Empty frames still really copy/read back; capture mode restores their console afterward.
 unsigned old_begins=begins;assert(!submit()&&begins==old_begins+1&&!presenting&&panel==before);
 assert(!query(0)&&out[1]==2&&out[9]==2);
 a.scalarInputCount=0;a.scalarOutputCount=1;assert(!call(c,3,a));auto*s=surfaces[(unsigned)out[0]-100];
 for(uint32_t y=0;y<1624;y++){auto*p=(uint32_t*)(s->kpixels+y*s->info.bytesPerRow);for(uint32_t x=0;x<750;x++)p[x]=0xff112233;}
 put(0x54,s->id);put(0x6c,750);put(0x70,1624);put(0xcc,750);put(0xd0,1624);
 assert(!submit()&&presenting);fake_now+=10000000000ULL;
 assert(!query(1)&&presenting&&out[1]==3&&out[2]==1&&out[3]==720*1480&&out[11]==0);
 // A failed update does not increment completed frames or erase the previous real content.
 fail_update=true;assert(submit()==kIOReturnError);fail_update=false;
 assert(!query(0)&&out[1]==3&&out[6]==1&&out[7]==kIOReturnError&&out[12]==0xfeedface);
 assert(!c->clientClose()&&!presenting);c->release();fb->release();actor_uid=501;
 puts("M73 actual observation: root-only ABI/canaries, busy/shape rejection, delayed blank recovery, genuine black copy/restore, real-content takeover and failed-frame accounting PASS");
}
