/* M70: HackiOS AppleKeyStore discovery/events and fixed no-passcode test profile.
 * Protocol origin: oosexgang/hackios-xnu-kernel a3384e031eb1e605cf37adaefc19991f04f6274b,
 * MiniAppleKeyStore.cpp, APSL-2.0. No persisted bags, credentials or key wrapping.
 */
#ifndef XC70_KEYSTORE_H
#define XC70_KEYSTORE_H
#ifndef XC70_HOST_TEST
#include <IOKit/IOMemoryDescriptor.h>
#endif
static uint32_t xc70_notify;
static uint64_t xc70_logged[4];
static size_t xc70_der_value(uint8_t *p,size_t n,const char *key,uint8_t value) {
 size_t k=strlen(key);p[n++]=0x30;p[n++]=(uint8_t)(k+5);p[n++]=0x0c;p[n++]=(uint8_t)k;
 memcpy(p+n,key,k);n+=k;p[n++]=2;p[n++]=1;p[n++]=value;return n;
}
static size_t xc70_der(uint8_t *p,bool config) {
 size_t n=2;
 if(config){n=xc70_der_value(p,n,"bd",0);n=xc70_der_value(p,n,"gp",0);n=xc70_der_value(p,n,"mua",10);}
 else {
  const char *keys[]={"sb","sr","ss","sas","sfa","sgs","sls","sgpe","srcd"};
  for(unsigned i=0;i<9;i++)n=xc70_der_value(p,n,keys[i],i==2?6:i==6?3:0);
 }
 p[0]=0x31;p[1]=(uint8_t)(n-2);return n;
}
class AppleKeyStore:public IOService {
 OSDeclareDefaultStructors(AppleKeyStore);
public:
 bool start(IOService *provider) APPLE_KEXT_OVERRIDE {
  if(!IOService::start(provider))return false;
  setProperty(kIOUserClientClassKey,"AppleKeyStoreUserClient");setName("AppleKeyStore");registerService();
  IOLog("XCOVER5 M70 AKS_READY path=IOService:/IOResources/AppleKeyStore; volatile no-passcode test profile\n");
  return true;
 }
};
OSDefineMetaClassAndStructors(AppleKeyStore,IOService);
class AppleKeyStoreUserClient:public IOUserClient {
 OSDeclareDefaultStructors(AppleKeyStoreUserClient);
 static IOReturn answer(IOExternalMethodArguments *a,const uint8_t *p,size_t n) {
  if(a->structureOutputDescriptor) {
   IOMemoryDescriptor *out=a->structureOutputDescriptor;
   if(out->getLength()<n)return kIOReturnNoSpace;
   if(out->getLength()>65536)return kIOReturnBadArgument;
   IOReturn rc=out->prepare();if(rc)return rc;
   bool complete=out->writeBytes(0,p,n)==n;out->complete();
   if(!complete)return kIOReturnError;
   a->structureOutputDescriptorSize=(uint32_t)n;return kIOReturnSuccess;
  }
  if(!a->structureOutput||a->structureOutputSize<n)return kIOReturnNoSpace;
  memcpy(a->structureOutput,p,n);a->structureOutputSize=(uint32_t)n;return kIOReturnSuccess;
 }
public:
 bool initWithTask(task_t task,void *security,UInt32 type,OSDictionary *props) APPLE_KEXT_OVERRIDE {
  if(!IOUserClient::initWithTask(task,security,type,props))return false;
  IOLog("XCOVER5 M70 AKS_OPEN pid=%d type=%u\n",proc_selfpid(),type);return true;
 }
 IOReturn clientClose(void) APPLE_KEXT_OVERRIDE {if(!isInactive())terminate();return kIOReturnSuccess;}
 IOReturn registerNotificationPort(mach_port_t port,UInt32 type,io_user_reference_t ref) APPLE_KEXT_OVERRIDE {
  (void)type;(void)ref;releaseNotificationPort(port);return kIOReturnSuccess;
 }
 IOReturn externalMethod(uint32_t sel,IOExternalMethodArguments *a,IOExternalMethodDispatch *,OSObject *,void *) APPLE_KEXT_OVERRIDE {
  if(!a||a->scalarInputCount>16||a->scalarOutputCount>16||
     (a->scalarInputCount&&!a->scalarInput)||(a->scalarOutputCount&&!a->scalarOutput)||
     a->structureInputDescriptor||a->structureInputSize>4096||a->structureOutputSize>65536)return kIOReturnBadArgument;
  if(sel<256 && !(__sync_fetch_and_or(&xc70_logged[sel/64],1ULL<<(sel%64))&(1ULL<<(sel%64))))
   IOLog("XCOVER5 M70 AKS pid=%d selector=%x scalars=%u/%u struct=%u/%u\n",proc_selfpid(),sel,a->scalarInputCount,a->scalarOutputCount,a->structureInputSize,a->structureOutputSize);
  uint8_t der[128];uint64_t *out=a->scalarOutput;
  switch(sel) {
   case 0:case 0x1a:case 0x1b:case 0x64:case 0x65:case 0x73:return kIOReturnSuccess;
   case 7:case 0x0e:case 0x28:case 0x67:
    if(!a->scalarOutputCount)return kIOReturnBadArgument;
    out[0]=sel==7?6:sel==0x67?__sync_val_compare_and_swap(&xc70_notify,0,0):0;
    a->scalarOutputCount=1;return kIOReturnSuccess;
   case 0x11:case 0x23:case 0x1f:return answer(a,der,xc70_der(der,sel==0x1f));
   case 0x17: {
    static const uint8_t uuid[16]={0x72,0x65,0x64,0x77,0x6f,0x6f,0x64,0,0x6b,0x65,0x79,0x62,0x61,0x67,0,1};
    return answer(a,uuid,sizeof(uuid));
   }
   case 0x66:__sync_lock_test_and_set(&xc70_notify,1);return kIOReturnSuccess;
   default:return kIOReturnUnsupported;
  }
 }
};
OSDefineMetaClassAndStructors(AppleKeyStoreUserClient,IOUserClient);
static void XCoverAppleKeyStoreStart(void) {
 IOService *resources=IOService::getResourceService();AppleKeyStore *store=OSTypeAlloc(AppleKeyStore);
 if(resources&&store&&store->init()&&store->attach(resources)) {
  if(!store->start(resources))store->detach(resources);
 }else IOLog("XCOVER5 M70 AKS_START_FAILED resources=%u\n",resources!=NULL);
 OSSafeReleaseNULL(store);
}
#endif
