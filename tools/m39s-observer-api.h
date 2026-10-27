#ifndef M39S_OBSERVER_API_H
#define M39S_OBSERVER_API_H
extern void m39s_dump(void);
extern void m39s_activate(void);
extern unsigned m39s_calibration_count(void);
/* Call from main, outside the interposing dylib. */
typedef void *m39s_cal_object;
extern m39s_cal_object xpc_dictionary_create(const char *const *,const m39s_cal_object *,unsigned long);
extern void xpc_dictionary_set_string(m39s_cal_object,const char *,const char *);
extern const char *xpc_dictionary_get_string(m39s_cal_object,const char *);
extern void xpc_release(m39s_cal_object);
static int m39s_calibrate(void) {
    m39s_cal_object dictionary=xpc_dictionary_create(NULL,NULL,0);
    if(!dictionary)return 0;
    xpc_dictionary_set_string(dictionary,"org.xcover5.m39s.calibration","m39s-real-value");
    const char *value=xpc_dictionary_get_string(dictionary,"org.xcover5.m39s.calibration");
    int result=value&&!strcmp(value,"m39s-real-value");xpc_release(dictionary);return result;
}
#endif
