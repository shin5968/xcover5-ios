/* Adapted from userland/src/svc_test.c, OOSEX GANG (c) 2026, MIT.
 * Upstream a79ff0772a3454fd1ef127e181e5b3bce6c9ce18; see third_party/hackios-userland/.
 * Preserve the upstream application-domain API sequence. The caller additionally
 * requires an on-disk file, fresh-exec read, and cleanup, which upstream does not.
 */
#ifndef XCOVER5_HACKIOS_PREFERENCES_H
#define XCOVER5_HACKIOS_PREFERENCES_H
static void hackios_preferences_set(CFStringRef key, CFPropertyListRef value, CFStringRef app) {
    CFPreferencesSetAppValue(key,value,app);
}
static Boolean hackios_preferences_sync(CFStringRef app) {
    return CFPreferencesAppSynchronize(app);
}
static CFPropertyListRef hackios_preferences_copy(CFStringRef key, CFStringRef app) {
    return CFPreferencesCopyAppValue(key,app);
}
#endif
