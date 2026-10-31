/* Read-only evidence for the newly imported services and local UI identity. */
#include <dlfcn.h>
#include <CoreFoundation/CoreFoundation.h>
static void m72_portable_probe(void){
 void *lib=dlopen("/System/Library/Frameworks/IOKit.framework/IOKit",RTLD_LAZY|RTLD_LOCAL);
 typedef CFMutableDictionaryRef(*matching_fn)(const char*);
 typedef uint32_t(*service_fn)(uint32_t,CFDictionaryRef);
 typedef uint32_t(*path_fn)(uint32_t,const char*);
 typedef CFTypeRef(*property_fn)(uint32_t,CFStringRef,CFAllocatorRef,uint32_t);
 typedef int(*release_fn)(uint32_t);
 matching_fn matching=lib?(matching_fn)dlsym(lib,"IOServiceMatching"):NULL;
 service_fn service=lib?(service_fn)dlsym(lib,"IOServiceGetMatchingService"):NULL;
 path_fn path=lib?(path_fn)dlsym(lib,"IORegistryEntryFromPath"):NULL;
 property_fn property=lib?(property_fn)dlsym(lib,"IORegistryEntryCreateCFProperty"):NULL;
 release_fn release=lib?(release_fn)dlsym(lib,"IOObjectRelease"):NULL;
 printf("XCOVER5 M72 PROBE iokit=%u symbols=%u\n",lib!=NULL,matching&&service&&path&&property&&release);
 if(matching&&service&&path&&property&&release){
  const char*names[]={"IONetworkStack","AppleKeyStore","IOMobileFramebuffer","IOSurfaceRoot"};
  for(unsigned i=0;i<4;i++){CFMutableDictionaryRef dict=matching(names[i]);uint32_t port=dict?service(0,dict):0;
   printf("XCOVER5 M72 SERVICE name=%s found=%u\n",names[i],port!=0);if(port)release(port);}
  uint32_t product=path(0,"IODeviceTree:/product");
  CFTypeRef value=product?property(product,CFSTR("product-id"),kCFAllocatorDefault,0):NULL;
  long length=value&&CFGetTypeID(value)==CFDataGetTypeID()?(long)CFDataGetLength((CFDataRef)value):-1;
  printf("XCOVER5 M72 IDENTITY product_node=%u model_product_id_bytes=%ld expected=20\n",product!=0,length);
  if(value)CFRelease(value);if(product)release(product);
 }
 if(lib)dlclose(lib);
 struct stat st;errno=0;int rc=stat("/dev/redwood-touch",&st),error=errno;
 printf("XCOVER5 M72 INPUT_NODE stat=%d errno=%d; physical touch backend pending\n",rc,error);
}
