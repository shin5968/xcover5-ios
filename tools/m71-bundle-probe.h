/* Observe real CFBundle creation from restored metadata; never query a NULL bundle. */
#include <CoreFoundation/CoreFoundation.h>
#include <stdbool.h>
static void m71_bundle_probe(void) {
 const char *paths[]={
  "/System/Library/Frameworks/CoreFoundation.framework",
  "/System/Library/Frameworks/UIKit.framework",
  "/System/Library/Frameworks/QuartzCore.framework",
  "/System/Library/PrivateFrameworks/UIKitCore.framework",
  "/System/Library/PrivateFrameworks/CoreUI.framework",
  "/System/Library/PrivateFrameworks/SpringBoard.framework",
  "/System/Library/PrivateFrameworks/SpringBoardHome.framework",
  "/System/Library/PrivateFrameworks/SpringBoardFoundation.framework"};
 for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);i++) {
  char file[512],identifier[128]={0};struct stat st;snprintf(file,sizeof(file),"%s/Info.plist",paths[i]);
  errno=0;int rc=stat(file,&st),error=errno;
  CFStringRef path=CFStringCreateWithCString(kCFAllocatorDefault,paths[i],kCFStringEncodingUTF8);
  CFURLRef url=path?CFURLCreateWithFileSystemPath(kCFAllocatorDefault,path,kCFURLPOSIXPathStyle,true):NULL;
  CFBundleRef bundle=url?CFBundleCreate(kCFAllocatorDefault,url):NULL;
  CFDictionaryRef info=bundle?CFBundleGetInfoDictionary(bundle):NULL;
  CFStringRef ident=bundle?CFBundleGetIdentifier(bundle):NULL;
  int named=ident&&CFStringGetCString(ident,identifier,sizeof(identifier),kCFStringEncodingUTF8);
  printf("XCOVER5 M71 BUNDLE path=%s stat=%d errno=%d bytes=%lld create=%d info=%d id=%s; metadata only, not UI readiness\n",
   paths[i],rc,error,rc?-1LL:(long long)st.st_size,bundle!=NULL,info!=NULL,named?identifier:"<none>");
  if(bundle)CFRelease(bundle);
  if(url)CFRelease(url);
  if(path)CFRelease(path);
 }
}
