// Owned IOKit contract harness; actual M70 service/query bodies included below.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <map>
#include <string>
#include <vector>
#define XC70_HOST_TEST 1
#define task_t MockTask
#define mach_port_t MockPort
using task_t=void*;using mach_port_t=void*;using UInt32=uint32_t;using io_user_reference_t=uint64_t;using IOReturn=int;
enum {kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNoSpace=2,kIOReturnError=3,kIOReturnUnsupported=4};
#define APPLE_KEXT_OVERRIDE override
#define OSDeclareDefaultStructors(C) public:C()=default;virtual ~C()=default;
#define OSDefineMetaClassAndStructors(C,B)
#define OSTypeAlloc(C) new C
#define OSSafeReleaseNULL(o) do{if(o){(o)->release();o=nullptr;}}while(0)
#define IOLog(...) ((void)0)
static int live=0,port_releases=0;static bool fail_start=false,have_resources=true;
struct OSObject{int refs=1;OSObject(){live++;}virtual ~OSObject(){live--;}void retain(){refs++;}void release(){assert(refs);if(!--refs)delete this;}};
struct OSDictionary:OSObject{};static const char*kIOUserClientClassKey="IOUserClientClass";
struct IOService;static IOService*resources;
struct IOService:OSObject{
 std::string name,client;IOService*provider=nullptr;bool inactive=false,registered=false;std::vector<IOService*>children;
 virtual bool init(){return true;}virtual bool start(IOService*){return !fail_start;}
 bool attach(IOService*p){provider=p;retain();p->children.push_back(this);return true;}
 void detach(IOService*p){for(auto i=p->children.begin();i!=p->children.end();i++)if(*i==this){p->children.erase(i);provider=nullptr;release();break;}}
 void setProperty(const char*k,const char*v){assert(!strcmp(k,kIOUserClientClassKey));client=v;}void setName(const char*s){name=s;}
 void registerService(){registered=true;}static IOService*getResourceService(){return have_resources?resources:nullptr;}
 bool isInactive(){return inactive;}void terminate(){inactive=true;}
 ~IOService(){for(auto*c:children){c->provider=nullptr;c->release();}}
};
struct IOMemoryDescriptor{size_t length,wrote=0;int prepared=0,completed=0;bool fail=false,short_write=false;std::vector<uint8_t>data;
 IOMemoryDescriptor(size_t n):length(n),data(n,0xee){}size_t getLength(){return length;}
 IOReturn prepare(){prepared++;return fail?kIOReturnError:0;}void complete(){completed++;}
 size_t writeBytes(size_t at,const void*p,size_t n){assert(at+n<=length);if(short_write)n--;memcpy(data.data()+at,p,n);wrote=n;return n;}};
struct IOExternalMethodDispatch{};
struct IOExternalMethodArguments{const uint64_t*scalarInput=nullptr;uint64_t*scalarOutput=nullptr;uint32_t scalarInputCount=0,scalarOutputCount=0;
 void*structureInput=nullptr,*structureOutput=nullptr;uint32_t structureInputSize=0,structureOutputSize=0;
 IOMemoryDescriptor*structureInputDescriptor=nullptr,*structureOutputDescriptor=nullptr;uint64_t structureOutputDescriptorSize=0;};
struct IOUserClient:IOService{
 virtual bool initWithTask(task_t,void*,UInt32,OSDictionary*){return true;}virtual IOReturn clientClose(){return 0;}
 virtual IOReturn registerNotificationPort(mach_port_t,UInt32,io_user_reference_t){return 0;}
 virtual IOReturn externalMethod(uint32_t,IOExternalMethodArguments*,IOExternalMethodDispatch*,OSObject*,void*){return 0;}
 void releaseNotificationPort(mach_port_t){port_releases++;}
};static int proc_selfpid(){return 6;}
#include "XCoverAppleKeyStore.h"
static std::map<std::string,unsigned> parse(const uint8_t*p,size_t n){
 assert(n>=2&&p[0]==0x31&&p[1]+2==n);std::map<std::string,unsigned>d;size_t i=2;
 while(i<n){assert(p[i++]==0x30);size_t len=p[i++],end=i+len;assert(end<=n&&p[i++]==0x0c);size_t k=p[i++];std::string key((const char*)p+i,k);i+=k;
  assert(p[i++]==2&&p[i++]==1);d[key]=p[i++];assert(i==end);}return d;
}
int main(){
 resources=new IOService;resources->name="IOResources";int before=live;
 have_resources=false;XCoverAppleKeyStoreStart();assert(live==before);have_resources=true;
 fail_start=true;XCoverAppleKeyStoreStart();assert(live==before&&resources->children.empty());fail_start=false;
 XCoverAppleKeyStoreStart();assert(resources->children.size()==1);auto*s=dynamic_cast<AppleKeyStore*>(resources->children[0]);
 assert(s&&s->registered&&s->name=="AppleKeyStore"&&s->client=="AppleKeyStoreUserClient"&&s->provider==resources);
 auto*c=new AppleKeyStoreUserClient;assert(c->initWithTask((void*)1,nullptr,0,nullptr));
 IOExternalMethodArguments a;uint64_t value[2]={0,0xabc};a.scalarOutput=value;a.scalarOutputCount=1;
 auto call=[&](unsigned sel){return c->externalMethod(sel,&a,nullptr,nullptr,nullptr);};
 assert(!call(7)&&value[0]==6&&value[1]==0xabc);for(unsigned sel:{0x0eU,0x28U,0x67U}){a.scalarOutputCount=1;assert(!call(sel)&&value[0]==0);}
 assert(!call(0x66));a.scalarOutputCount=1;assert(!call(0x67)&&value[0]==1);
 a.scalarOutputCount=0;assert(call(7)==kIOReturnBadArgument);a.scalarOutputCount=1;a.scalarOutput=nullptr;assert(call(7)==kIOReturnBadArgument);a.scalarOutputCount=0;
 uint8_t bytes[132];memset(bytes,0xee,sizeof(bytes));a.structureOutput=bytes+2;a.structureOutputSize=128;
 assert(!call(0x11));size_t n=a.structureOutputSize;auto d=parse(bytes+2,n);assert(d.size()==9&&d["ss"]==6&&d["sls"]==3&&d["sb"]==0);
 assert(bytes[0]==0xee&&bytes[1]==0xee&&bytes[n+2]==0xee);a.structureOutputSize=1;assert(call(0x11)==kIOReturnNoSpace);
 a.structureOutputSize=128;assert(!call(0x1f));d=parse(bytes+2,a.structureOutputSize);assert(d.size()==3&&d["mua"]==10);
 a.structureOutputSize=128;assert(!call(0x17)&&a.structureOutputSize==16);
 IOMemoryDescriptor out(65536);a.structureOutput=nullptr;a.structureOutputSize=0;a.structureOutputDescriptor=&out;
 assert(!call(0x23)&&out.prepared==1&&out.completed==1&&out.wrote==n&&a.structureOutputDescriptorSize==n);parse(out.data.data(),n);
 IOMemoryDescriptor tiny(1);a.structureOutputDescriptor=&tiny;assert(call(0x11)==kIOReturnNoSpace&&!tiny.prepared);
 IOMemoryDescriptor fail(128);fail.fail=true;a.structureOutputDescriptor=&fail;assert(call(0x11)==kIOReturnError&&fail.prepared==1&&!fail.completed&&!fail.wrote);
 IOMemoryDescriptor shortout(128);shortout.short_write=true;a.structureOutputDescriptor=&shortout;assert(call(0x11)==kIOReturnError&&shortout.completed==1);
 IOMemoryDescriptor huge(65537);a.structureOutputDescriptor=&huge;assert(call(0x11)==kIOReturnBadArgument&&!huge.prepared);
 a.structureOutputDescriptor=nullptr;for(unsigned sel:{8U,9U,0x0aU,0x0bU,0x0cU,0x20U,0xffU})assert(call(sel)==kIOReturnUnsupported);
 assert(!c->registerNotificationPort((void*)1,0,0)&&port_releases==1);assert(!c->clientClose()&&c->inactive);c->release();resources->release();assert(live==0);
 puts("M70 actual service: IOResources identity, task client, fixed-profile DER/scalars, inline/OOL bounds and failures, unsupported key operations, port/close cleanup PASS");
}
