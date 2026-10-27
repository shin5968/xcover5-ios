/* M41 loads Foundation only after the unchanged M39+M40 sequence returns62.
 * Typed objc_msgSend calls avoid a static Foundation dependency at process entry.
 * They invoke real runtime classes; there are no framework or timer stubs. */
#include <CoreFoundation/CoreFoundation.h>
#include <objc/runtime.h>
#include <objc/message.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int m40_baseline_main(int,char **);
static _Atomic unsigned ticks,bad_callback;
static pthread_t main_thread;
static id timer_payload;
static SEL selector(const char *name){return sel_registerName(name);}
static id send0(id object,const char *name){return ((id(*)(id,SEL))objc_msgSend)(object,selector(name));}
static id send1(id object,const char *name,id argument){return ((id(*)(id,SEL,id))objc_msgSend)(object,selector(name),argument);}
static void void0(id object,const char *name){((void(*)(id,SEL))objc_msgSend)(object,selector(name));}
static int equal(id object,id expected){return ((BOOL(*)(id,SEL,id))objc_msgSend)(object,selector("isEqual:"),expected)!=NO;}
static void fail(int stage,const char *where){fprintf(stderr,"XCOVER5 M41 FAIL stage=%d where=%s\n",stage,where);_exit(stage);}
static id required_class(const char *name){id cls=(id)objc_getClass(name);if(!cls){fprintf(stderr,"M41 missing class=%s\n",name);fail(191,"Foundation_class");}return cls;}
static id string(const char *text){return ((id(*)(id,SEL,const char*))objc_msgSend)(required_class("NSString"),selector("stringWithUTF8String:"),text);}
static id future(double seconds){return ((id(*)(id,SEL,double))objc_msgSend)(required_class("NSDate"),selector("dateWithTimeIntervalSinceNow:"),seconds);}
static void fire(id self,SEL command,id timer){
    (void)self;(void)command;
    if(!pthread_equal(pthread_self(),main_thread) || !equal(send0(timer,"userInfo"),timer_payload))atomic_store(&bad_callback,1);
    unsigned count=atomic_fetch_add(&ticks,1)+1;
    printf("XCOVER5 M41 TIMER fired=%u main_thread=%d\n",count,pthread_equal(pthread_self(),main_thread));
    if(count>=3)void0(timer,"invalidate");
}
static void run_once(id loop,id mode,double seconds){
    ((BOOL(*)(id,SEL,id,id))objc_msgSend)(loop,selector("runMode:beforeDate:"),mode,future(seconds));
}
static int run_foundation(void){
    alarm(15);
    puts("XCOVER5 M41 BEGIN: loading Foundation after M39+M40 PASS");
    void *handle=dlopen("/System/Library/Frameworks/Foundation.framework/Foundation",RTLD_NOW|RTLD_LOCAL);
    if(!handle){fprintf(stderr,"M41 dlopen error=%s\n",dlerror());fail(190,"Foundation_dlopen");}
    id pool=send0(required_class("NSAutoreleasePool"),"new");if(!pool)fail(192,"autorelease_pool");
    id text=string("xcover5");
    unsigned long length=((unsigned long(*)(id,SEL))objc_msgSend)(text,selector("length"));
    id array=send0(required_class("NSMutableArray"),"array");
    send1(array,"addObject:",text);
    id number=((id(*)(id,SEL,int))objc_msgSend)(required_class("NSNumber"),selector("numberWithInt:"),41);
    send1(array,"addObject:",number);
    unsigned long count=((unsigned long(*)(id,SEL))objc_msgSend)(array,selector("count"));
    id found=((id(*)(id,SEL,unsigned long))objc_msgSend)(array,selector("objectAtIndex:"),0);
    id dictionary=send0(required_class("NSMutableDictionary"),"dictionary");id key=string("proof");
    ((void(*)(id,SEL,id,id))objc_msgSend)(dictionary,selector("setObject:forKey:"),text,key);
    int integer=((int(*)(id,SEL))objc_msgSend)(number,selector("intValue"));
    if(length!=7 || count!=2 || integer!=41 || !equal(found,text) || !equal(send1(dictionary,"objectForKey:",key),text))fail(193,"strings_collections");
    puts("XCOVER5 M41 OBJECTS PASS: NSString + NSNumber + array + dictionary");
    Class base=(Class)required_class("NSObject");Class target_class=objc_allocateClassPair(base,"XC41TimerTarget",0);
    if(!target_class || !class_addMethod(target_class,selector("timerFired:"),(IMP)fire,"v24@0:8@16"))fail(194,"timer_target_class");
    objc_registerClassPair(target_class);id target=send0((id)target_class,"new");
    id *mode_address=(id*)dlsym(handle,"NSDefaultRunLoopMode");
    if(!target || !mode_address || !*mode_address)fail(195,"timer_target_or_mode");
    id loop=send0(required_class("NSRunLoop"),"currentRunLoop");timer_payload=string("m41-timer-payload");
    main_thread=pthread_self();atomic_store(&ticks,0);atomic_store(&bad_callback,0);
    id timer=((id(*)(id,SEL,double,id,SEL,id,BOOL))objc_msgSend)(required_class("NSTimer"),selector("timerWithTimeInterval:target:selector:userInfo:repeats:"),0.02,target,selector("timerFired:"),timer_payload,YES);
    if(!loop || !timer)fail(195,"timer_or_runloop");
#ifdef M41_HOST_TEST
    if(!getenv("M41_TEST_NO_SCHEDULE"))
#endif
    ((void(*)(id,SEL,id,id))objc_msgSend)(loop,selector("addTimer:forMode:"),timer,*mode_address);
    CFAbsoluteTime start=CFAbsoluteTimeGetCurrent();unsigned iterations=0;
    while(atomic_load(&ticks)<3 && CFAbsoluteTimeGetCurrent()-start<4.0 && iterations++<100){
        run_once(loop,*mode_address,0.05);usleep(1000);
    }
    void0(timer,"invalidate");
    unsigned before=atomic_load(&ticks);
    if(before!=3 || atomic_load(&bad_callback))fail(196,"timer_callbacks_or_thread_or_payload");
    double elapsed=CFAbsoluteTimeGetCurrent()-start;
    if(elapsed<0.02 || elapsed>4.0)fail(197,"timer_elapsed");
    CFAbsoluteTime stop=CFAbsoluteTimeGetCurrent();iterations=0;
    while(CFAbsoluteTimeGetCurrent()-stop<0.10 && iterations++<150){run_once(loop,*mode_address,0.02);usleep(1000);}
    if(atomic_load(&ticks)!=before || ((BOOL(*)(id,SEL))objc_msgSend)(timer,selector("isValid")))fail(198,"timer_invalidation");
    printf("XCOVER5 M41 RUNLOOP PASS: callbacks=%u elapsed_ms=%.1f invalidate=yes\n",before,elapsed*1000.0);
    void0(target,"release");void0(pool,"drain");
    /* Keep Foundation resident for process lifetime; unloading ObjC classes is not tested. */
    puts("XCOVER5 M41 PASS: M39+M40 + Foundation objects + RunLoop + three timer callbacks + cancel");
    return 63;
}
int main(int argc,char **argv){
    setvbuf(stdout,NULL,_IONBF,0);setvbuf(stderr,NULL,_IONBF,0);
    int result=m40_baseline_main(argc,argv);
    if(argc!=1 || result!=62)return result;
    return run_foundation();
}
