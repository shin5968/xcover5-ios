/* Separate image: verifies dyld applied the main executable's interpose tuple.
 * No connection, service lookup or preference request is made by this test. */
#include <string.h>
typedef void *m39s_xpc;
extern m39s_xpc xpc_dictionary_create(const char *const *,const m39s_xpc *,unsigned long);
extern void xpc_dictionary_set_string(m39s_xpc,const char *,const char *);
extern const char *xpc_dictionary_get_string(m39s_xpc,const char *);
extern void xpc_release(m39s_xpc);
int m39s_calibrate(void) {
    m39s_xpc dictionary=xpc_dictionary_create(0,0,0);
    if(!dictionary)return 0;
    xpc_dictionary_set_string(dictionary,"org.xcover5.m39s.calibration","m39s-real-value");
    const char *value=xpc_dictionary_get_string(dictionary,"org.xcover5.m39s.calibration");
    int result=value&&!strcmp(value,"m39s-real-value");xpc_release(dictionary);return result;
}
