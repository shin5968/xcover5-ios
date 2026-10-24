/* Verify the opaque storage reserved by sweet-mutex.S against the iOS SDK. */
#include <pthread.h>
#include <stdint.h>
_Static_assert(sizeof(pthread_t) == 8, "pthread handle slot");
_Static_assert(sizeof(pthread_mutex_t) <= 128, "mutex storage capacity");
_Static_assert(_Alignof(pthread_mutex_t) <= 16, "mutex storage alignment");
_Static_assert(sizeof(void *) == 8, "arm64 pointers");

#include <mach/mach.h>
#include <stddef.h>
_Static_assert(sizeof(mach_msg_header_t)==24, "Mach header");
_Static_assert(offsetof(mach_msg_header_t,msgh_local_port)==12, "local port offset");
_Static_assert(offsetof(mach_msg_header_t,msgh_id)==20, "message id offset");
_Static_assert(sizeof(mach_port_t)==4, "port name width");
_Static_assert(MACH_PORT_RIGHT_RECEIVE==1 && MACH_MSG_TYPE_MAKE_SEND==20 && MACH_MSG_TYPE_COPY_SEND==19, "port rights");
_Static_assert((MACH_SEND_MSG|MACH_SEND_TIMEOUT)==0x11, "send options");
_Static_assert((MACH_RCV_MSG|MACH_RCV_TIMEOUT)==0x102, "receive options");

#include <mach/task_special_ports.h>
_Static_assert(TASK_BOOTSTRAP_PORT==4, "task bootstrap slot");
_Static_assert(MACH_MSG_TYPE_MAKE_SEND_ONCE==21 && MACH_MSG_TYPE_MOVE_SEND_ONCE==18, "send once dispositions");
