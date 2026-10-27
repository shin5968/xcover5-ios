/* Test-process XPC observation. Replies, handlers, arguments and errno preserved.
 * No daemon, Apple file, sandbox policy or synchronization result is patched. */
#ifndef M39S_REPLY_OBSERVER_H
#define M39S_REPLY_OBSERVER_H
#ifndef M39S_HOST
#include <dispatch/dispatch.h>
#if defined(__arm64e__)
#error M39S interpose tuples require the non-PAC arm64 ABI
#endif
typedef void *m39s_xpc;
extern m39s_xpc xpc_get_type(m39s_xpc);
extern const char *xpc_dictionary_get_string(m39s_xpc,const char *);
extern m39s_xpc xpc_dictionary_get_value(m39s_xpc,const char *);
extern char *xpc_copy_description(m39s_xpc);
extern m39s_xpc xpc_connection_send_message_with_reply_sync(m39s_xpc,m39s_xpc);
extern void xpc_connection_send_message_with_reply(m39s_xpc,m39s_xpc,dispatch_queue_t,void (^)(m39s_xpc));
extern const char _xpc_type_dictionary[];
extern const char _xpc_type_error[];
#endif
#define M39S_CAP 8U
struct m39s_event { _Atomic unsigned ready; char origin[16],description[513],type[97]; unsigned null_description,truncated; };
static struct m39s_event m39s_events[M39S_CAP];
static _Atomic unsigned m39s_active,m39s_total,m39s_sync_calls,m39s_async_calls,m39s_getter_calls,m39s_key_calls,m39s_empty_keys,m39s_dicts,m39s_errors,m39s_calibration_hits;
static unsigned m39s_copy(char *dst,size_t cap,const char *src) {
    size_t n=src?strnlen(src,cap):0;
    if(cap){size_t z=n<cap?n:cap-1;for(size_t i=0;i<z;i++){unsigned char c=(unsigned char)src[i];dst[i]=c>=32&&c<=126?(char)c:'?';}dst[z]=0;}
    return n==cap;
}
static void m39s_record(const char *origin,const char *description,const char *type) {
    unsigned slot=atomic_fetch_add_explicit(&m39s_total,1,memory_order_relaxed);
    if(slot>=M39S_CAP)return;
    struct m39s_event *e=&m39s_events[slot];
    m39s_copy(e->origin,sizeof(e->origin),origin);
    e->null_description=description==NULL;
    e->truncated=m39s_copy(e->description,sizeof(e->description),description);
    m39s_copy(e->type,sizeof(e->type),type);
    atomic_store_explicit(&e->ready,1,memory_order_release);
}
static void m39s_observe_reply(const char *origin,m39s_xpc reply) {
    if(!atomic_load_explicit(&m39s_active,memory_order_relaxed)||!reply)return;
    m39s_xpc kind=xpc_get_type(reply);
    if(kind==(m39s_xpc)_xpc_type_dictionary){
        atomic_fetch_add_explicit(&m39s_dicts,1,memory_order_relaxed);
        m39s_xpc value=xpc_dictionary_get_value(reply,"CFPreferencesErrorType");
        const char *description=xpc_dictionary_get_string(reply,"CFPreferencesErrorDescription");
        if(value||description){char *type=value?xpc_copy_description(value):NULL;m39s_record(origin,description,type);free(type);}
    }else if(kind==(m39s_xpc)_xpc_type_error){
        atomic_fetch_add_explicit(&m39s_errors,1,memory_order_relaxed);
        char *description=xpc_copy_description(reply);m39s_record(origin,description,"XPC_ERROR");free(description);
    }
}
static const char *m39s_get_string(m39s_xpc dictionary,const char *key) {
    const char *result=xpc_dictionary_get_string(dictionary,key);int saved_errno=errno;
    if(key&&!strcmp(key,"org.xcover5.m39s.calibration"))atomic_fetch_add_explicit(&m39s_calibration_hits,1,memory_order_relaxed);
    if(atomic_load_explicit(&m39s_active,memory_order_relaxed)){
        atomic_fetch_add_explicit(&m39s_getter_calls,1,memory_order_relaxed);
        if(key&&!strcmp(key,"CFPreferencesErrorDescription")){
            atomic_fetch_add_explicit(&m39s_key_calls,1,memory_order_relaxed);
            m39s_xpc value=xpc_dictionary_get_value(dictionary,"CFPreferencesErrorType");
            if(result||value){char *type=value?xpc_copy_description(value):NULL;m39s_record("error-getter",result,type);free(type);}
            else atomic_fetch_add_explicit(&m39s_empty_keys,1,memory_order_relaxed);
        }
    }
    errno=saved_errno;return result;
}
static m39s_xpc m39s_send_sync(m39s_xpc connection,m39s_xpc message) {
    int active=atomic_load_explicit(&m39s_active,memory_order_relaxed);
    if(active)atomic_fetch_add_explicit(&m39s_sync_calls,1,memory_order_relaxed);
    m39s_xpc reply=xpc_connection_send_message_with_reply_sync(connection,message);int saved_errno=errno;
    if(active)m39s_observe_reply("sync-reply",reply);
    errno=saved_errno;return reply;
}
static void m39s_send_async(m39s_xpc connection,m39s_xpc message,dispatch_queue_t queue,void (^handler)(m39s_xpc)) {
    int saved_errno=errno;
    if(!atomic_load_explicit(&m39s_active,memory_order_relaxed)||!handler){xpc_connection_send_message_with_reply(connection,message,queue,handler);return;}
    atomic_fetch_add_explicit(&m39s_async_calls,1,memory_order_relaxed);
    errno=saved_errno;
    xpc_connection_send_message_with_reply(connection,message,queue,^(m39s_xpc reply){
        int callback_errno=errno;m39s_observe_reply("async-reply",reply);errno=callback_errno;handler(reply);
    });
}
#ifndef M39S_HOST
/* dyld's two-pointer interposing section ABI; no private SDK header needed.
 * Reference: apple-oss-distributions/dyld include/mach-o/dyld-interposing.h. */
__attribute__((used,section("__DATA,__interpose,interposing")))
static const struct {const void *replacement,*original;} m39s_interposers[]={
    {(const void *)m39s_get_string,(const void *)xpc_dictionary_get_string},
    {(const void *)m39s_send_sync,(const void *)xpc_connection_send_message_with_reply_sync},
    {(const void *)m39s_send_async,(const void *)xpc_connection_send_message_with_reply}
};
#endif
static void m39s_snapshot_dump(void) {
    int saved_errno=errno;
    unsigned total=atomic_load_explicit(&m39s_total,memory_order_acquire),stored=total<M39S_CAP?total:M39S_CAP,inflight=0;
    printf("XCOVER5 M39S FINAL_REPLIES calibration=%u sync=%u async=%u getters=%u error_keys=%u empty_keys=%u dictionaries=%u xpc_errors=%u\n",
        atomic_load(&m39s_calibration_hits),atomic_load(&m39s_sync_calls),atomic_load(&m39s_async_calls),atomic_load(&m39s_getter_calls),atomic_load(&m39s_key_calls),atomic_load(&m39s_empty_keys),atomic_load(&m39s_dicts),atomic_load(&m39s_errors));
    for(unsigned i=0;i<stored;i++){
        struct m39s_event *e=&m39s_events[i];if(!atomic_load_explicit(&e->ready,memory_order_acquire)){inflight++;continue;}
        printf("M39S REPLY seq=%u via=%s null=%u truncated=%u type=%s\n",i,e->origin,e->null_description,e->truncated,e->type);
        printf("M39S DESCRIPTION seq=%u text=%s\n",i,e->description);
    }
    printf("XCOVER5 M39S FINAL_END total=%u stored=%u overflow=%u inflight=%u\n",total,stored,total-stored,inflight);
    errno=saved_errno;
}
#endif
