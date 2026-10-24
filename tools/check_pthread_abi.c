/* Verify the opaque storage reserved by sweet-mutex.S against the iOS SDK. */
#include <pthread.h>
#include <stdint.h>
_Static_assert(sizeof(pthread_t) == 8, "pthread handle slot");
_Static_assert(sizeof(pthread_mutex_t) <= 128, "mutex storage capacity");
_Static_assert(_Alignof(pthread_mutex_t) <= 16, "mutex storage alignment");
_Static_assert(sizeof(void *) == 8, "arm64 pointers");
