"""Compile actual observer with mock XPC boundaries; deferred async lifetime too."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent
prefix=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdatomic.h>
#include <Block.h>
#define M39S_HOST 1
typedef void *m39s_xpc;typedef void *dispatch_queue_t;
static const char _xpc_type_dictionary[1],_xpc_type_error[1],other_kind[1];
struct object { const void *kind;const char *description;const char *error_type;};
static struct object normal={_xpc_type_dictionary,NULL,NULL},rejection={_xpc_type_dictionary,"write denied because exact reason","4"},xerror={_xpc_type_error,"connection interrupted",NULL};
static unsigned original_sync_calls,original_async_calls,handler_calls;
static m39s_xpc selected_reply;
static void (^pending)(m39s_xpc);
static m39s_xpc xpc_get_type(m39s_xpc o){errno=ERANGE;return (void*)((struct object*)o)->kind;}
static const char *xpc_dictionary_get_string(m39s_xpc o,const char *key){assert(key);errno=EAGAIN;return ((struct object*)o)->description;}
static m39s_xpc xpc_dictionary_get_value(m39s_xpc o,const char *key){assert(!strcmp(key,"CFPreferencesErrorType"));errno=EIO;return ((struct object*)o)->error_type?(void*)o:NULL;}
static char *xpc_copy_description(m39s_xpc o){struct object *v=o;errno=ENOSPC;return strdup(v->kind==_xpc_type_dictionary?v->error_type:v->description);}
static m39s_xpc xpc_connection_send_message_with_reply_sync(m39s_xpc c,m39s_xpc m){assert(c==(void*)11&&m==(void*)22);original_sync_calls++;errno=EINTR;return selected_reply;}
static void xpc_connection_send_message_with_reply(m39s_xpc c,m39s_xpc m,dispatch_queue_t q,void (^h)(m39s_xpc)){assert(c==(void*)11&&m==(void*)22&&q==(void*)33);original_async_calls++;if(h)pending=Block_copy(h);errno=EINTR;}
'''
test=r'''
int main(void){
 selected_reply=&rejection;
 assert(m39s_send_sync((void*)11,(void*)22)==&rejection&&errno==EINTR);
 assert(original_sync_calls==1&&atomic_load(&m39s_total)==0);
 atomic_store(&m39s_active,1);
 assert(m39s_send_sync((void*)11,(void*)22)==&rejection&&errno==EINTR);
 assert(original_sync_calls==2&&atomic_load(&m39s_sync_calls)==1&&atomic_load(&m39s_total)==1);
 assert(!strcmp(m39s_events[0].description,rejection.description)&&!strcmp(m39s_events[0].type,"4"));
 assert(m39s_get_string(&rejection,"CFPreferencesErrorDescription")==rejection.description&&errno==EAGAIN);
 assert(atomic_load(&m39s_key_calls)==1&&atomic_load(&m39s_total)==2);
 assert(m39s_get_string(&normal,"CFPreferencesErrorDescription")==NULL&&errno==EAGAIN);
 assert(atomic_load(&m39s_empty_keys)==1&&atomic_load(&m39s_total)==2);
 for(unsigned i=0;i<20;i++)m39s_get_string(&normal,"CFPreferencesErrorDescription");
 assert(atomic_load(&m39s_total)==2&&atomic_load(&m39s_empty_keys)==21);
 m39s_get_string(&normal,"org.xcover5.m39s.calibration");assert(atomic_load(&m39s_calibration_hits)==1);
 unsigned count=atomic_load(&m39s_total);selected_reply=&normal;
 assert(m39s_send_sync((void*)11,(void*)22)==&normal&&errno==EINTR&&atomic_load(&m39s_total)==count);
 m39s_send_async((void*)11,(void*)22,(void*)33,^(m39s_xpc reply){assert(reply==&rejection&&errno==E2BIG);handler_calls++;});
 assert(original_async_calls==1&&handler_calls==0&&errno==EINTR);
 errno=E2BIG;pending(&rejection);Block_release(pending);pending=NULL;
 assert(handler_calls==1&&atomic_load(&m39s_async_calls)==1&&atomic_load(&m39s_total)==count+1);
 m39s_send_async((void*)11,(void*)22,(void*)33,NULL);assert(original_async_calls==2&&pending==NULL);
 m39s_observe_reply("xpc-error",&xerror);assert(atomic_load(&m39s_errors)==1);
 struct object other={other_kind,"unread",NULL};count=atomic_load(&m39s_total);m39s_observe_reply("other",&other);m39s_observe_reply("null",NULL);assert(atomic_load(&m39s_total)==count);
 char longtext[800];memset(longtext,'r',799);longtext[300]='\n';longtext[799]=0;
 m39s_record("long",longtext,"4");assert(m39s_events[count].truncated&&strlen(m39s_events[count].description)==512&&m39s_events[count].description[300]=='?');
 for(unsigned i=0;i<12;i++)m39s_record("overflow","bounded","4");
 errno=EBUSY;m39s_snapshot_dump();assert(errno==EBUSY&&atomic_load(&m39s_total)>M39S_CAP);
 assert(!strcmp(rejection.description,"write denied because exact reason")&&normal.description==NULL);
 puts("M39S actual observer: original calls/arguments/return pointer/errno, delayed block lifetime, NULL/typed replies, bounded immutable copies PASS (host only)");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'test.c').write_text(prefix+(r/'m39s-reply-observer.h').read_text()+test)
 subprocess.run(['cc','-fblocks','-Wall','-Wextra','-Werror',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
