/* HackiOS MiniIONetworkStack a3384e031eb1e605cf37adaefc19991f04f6274b, APSL2.
 * InterfaceNamer discovery/client protocol; BSD interfaces retain their names.
 * This service does not advertise a NIC, Wi-Fi hardware or network connectivity.
 */
#ifndef XC72_NETWORK_H
#define XC72_NETWORK_H
#ifndef XC72_HOST_TEST
#include <IOKit/IOKitKeys.h>
#include <sys/proc.h>
#endif
class IONetworkStack:public IOService {
 OSDeclareDefaultStructors(IONetworkStack);
public:
 bool start(IOService *provider) APPLE_KEXT_OVERRIDE {
  if(!IOService::start(provider))return false;
  setProperty(kIOUserClientClassKey,"IONetworkStackUserClient");setName("IONetworkStack");registerService();
  IOLog("XCOVER5 M72 NETWORK_STACK path=IOService:/IOResources/IONetworkStack\n");return true;
 }
};
OSDefineMetaClassAndStructors(IONetworkStack,IOService);
class IONetworkStackUserClient:public IOUserClient {
 OSDeclareDefaultStructors(IONetworkStackUserClient);
public:
 bool start(IOService *provider) APPLE_KEXT_OVERRIDE {
  if(!IOUserClient::start(provider))return false;
  IOLog("XCOVER5 M72 NETWORK_OPEN pid=%d\n",proc_selfpid());return true;
 }
 IOReturn clientClose(void) APPLE_KEXT_OVERRIDE {if(!isInactive())terminate();return kIOReturnSuccess;}
 IOReturn setProperties(OSObject *) APPLE_KEXT_OVERRIDE {
  static unsigned logs;if(__sync_fetch_and_add(&logs,1)<4)IOLog("XCOVER5 M72 NETWORK_NAME unsupported; no IOKit interface to rename\n");
  return kIOReturnUnsupported;
 }
};
OSDefineMetaClassAndStructors(IONetworkStackUserClient,IOUserClient);
static void XCoverNetworkStackStart(void) {
 IOService *resources=IOService::getResourceService();IONetworkStack *stack=OSTypeAlloc(IONetworkStack);
 if(resources&&stack&&stack->init()&&stack->attach(resources)) {
  if(!stack->start(resources))stack->detach(resources);
 }else IOLog("XCOVER5 M72 NETWORK_START_FAILED resources=%u\n",resources!=NULL);
 OSSafeReleaseNULL(stack);
}
#endif
