/* Adapted from HackiOS a3384e031eb1e605cf37adaefc19991f04f6274b, APSL-2.0. */
/*
 * /dev/hakios-touch: a queue of touch samples (see sys/hakios.input.h).
 */
#ifndef XC72_HOST_TEST
#include <kern/clock.h>
#include <kern/locks.h>
#include <kern/thread_call.h>
#include <libkern/libkern.h>
#include <miscfs/devfs/devfs.h>
#include <sys/conf.h>
#include <sys/fcntl.h>
#include <sys/vnode.h>
#include <sys/errno.h>
#include <sys/proc.h>
#include <sys/systm.h>
#include <sys/uio.h>
#include <pexpert/pexpert.h>
#endif
#include "xcover_input.h"

#define TOUCH_QUEUE     512             /* records; a power of two */

/*
 * Boot-arg touch_lat=1: for measuring how long a touch takes to reach the panel, a line for every
 * sample posted ("tl: p TYPE FINGER X Y at US", the time in microseconds of mach_absolute_time),
 * to be matched with the window server's lines about reading it (userland/src/inject.c), drawing
 * (eagl.c) and the display driver's about the frame (MiniIOMobileFramebuffer.cpp): see
 * tools/latency.py.
 */
static uint32_t touch_lat = 2;          /* 2: not yet looked up */

static bool
latency_lines(void)
{
	if (touch_lat == 2) {
		uint32_t on = 0;

		touch_lat = PE_parse_boot_argn("touch_lat", &on, sizeof(on)) && on != 0;
	}
	return touch_lat != 0;
}

static LCK_GRP_DECLARE(touch_lck_grp, "hakios-touch");
static LCK_MTX_DECLARE(touch_lock, &touch_lck_grp);
static struct hakios_touch touch_queue[TOUCH_QUEUE];
static bool touch_reader;
static uint32_t touch_head, touch_tail;        /* read from head, add at tail */

static void
touch_post(uint32_t type, uint32_t finger, uint32_t x, uint32_t y, __unused bool from_driver)
{
	struct hakios_touch *t;

	lck_mtx_lock(&touch_lock);
	if (touch_tail - touch_head == TOUCH_QUEUE) {
		touch_head++;                   /* nobody reads: drop the oldest */
	}
	t = &touch_queue[touch_tail++ % TOUCH_QUEUE];
	t->time = mach_absolute_time();
	if (latency_lines()) {
		uint64_t ns;

		absolutetime_to_nanoseconds(t->time, &ns);
		printf("tl: p %u %u %u %u at %llu\n", type, finger, x, y, ns / 1000);
	}
	t->type = type;
	t->finger = finger;
	t->x = x > 65535 ? 65535 : x;
	t->y = y > 65535 ? 65535 : y;
	lck_mtx_unlock(&touch_lock);
	wakeup(&touch_queue);
}

void
hakios_touch_post(uint32_t type, uint32_t finger, uint32_t x, uint32_t y)
{
	touch_post(type, finger, x, y, true);
}

static int
touch_open(__unused dev_t dev, int flags, __unused int devtype, __unused struct proc *p)
{
 int error=0;lck_mtx_lock(&touch_lock);
 if(flags & FREAD){if(touch_reader)error=EBUSY;else touch_reader=true;}
 lck_mtx_unlock(&touch_lock);return error;
}
static int
touch_close(__unused dev_t dev, int flags, __unused int devtype, __unused struct proc *p)
{
 lck_mtx_lock(&touch_lock);if(flags & FREAD)touch_reader=false;lck_mtx_unlock(&touch_lock);return 0;
}

static int
touch_read(__unused dev_t dev, struct uio *uio, int ioflag)
{
	struct hakios_touch t;
	int error = 0, moved = 0;

	/* a buffer smaller than one record can never be served: say so, instead of blocking for data and then returning 0 (end of file) */
	if (uio_resid(uio) == 0) {
		return 0;
	}
	if (uio_resid(uio) < (user_ssize_t)sizeof(t)) {
		return EINVAL;
	}
	lck_mtx_lock(&touch_lock);
	while (touch_head == touch_tail) {
		if (ioflag & IO_NDELAY) { lck_mtx_unlock(&touch_lock); return EWOULDBLOCK; }
		error = msleep(&touch_queue, &touch_lock, PZERO | PCATCH, "hakios-touch", NULL);
		if (error) {
			lck_mtx_unlock(&touch_lock);
			return error;
		}
	}
	while (touch_head != touch_tail && uio_resid(uio) >= (user_ssize_t)sizeof(t)) {
		t = touch_queue[touch_head++ % TOUCH_QUEUE];
		lck_mtx_unlock(&touch_lock);
		error = uiomove((caddr_t)&t, sizeof(t), uio);
		lck_mtx_lock(&touch_lock);
		if (error) {
			/* the copy-out failed: put the record back at the head so a lost DOWN or UP does not leave a finger stuck (only if the ring still has room for it) */
			if (touch_tail - touch_head < TOUCH_QUEUE) {
				touch_queue[--touch_head % TOUCH_QUEUE] = t;
			}
			break;
		}
		moved++;
	}
	lck_mtx_unlock(&touch_lock);
	return moved ? 0 : error;
}

static int
touch_write(__unused dev_t dev, struct uio *uio, __unused int ioflag)
{
	struct hakios_touch t;
	int error = 0;
	if (uio_resid(uio) % sizeof(t)) return EINVAL;

	while (uio_resid(uio) >= (user_ssize_t)sizeof(t)) {
		error = uiomove((caddr_t)&t, sizeof(t), uio);
		if (error) {
			break;
		}
		if (t.type < HAKIOS_TOUCH_DOWN || t.type > HAKIOS_BUTTON_UP) {
			return EINVAL;
		}
		touch_post(t.type, t.finger, t.x, t.y, false);
	}
	return error;
}

static const struct cdevsw touch_cdevsw = {
	.d_open = touch_open, .d_close = touch_close, .d_read = touch_read, .d_write = touch_write,
	.d_ioctl = eno_ioctl, .d_stop = eno_stop, .d_reset = eno_reset, .d_select = eno_select,
	.d_mmap = eno_mmap, .d_strategy = eno_strat, .d_type = 0
};

void
hakios_input_init(void)
{
 int major = cdevsw_add(-1, &touch_cdevsw);
 if(major<0){printf("XCOVER5 M72 INPUT_FAILED cdev\n");return;}
 void *primary=devfs_make_node(makedev(major,0),DEVFS_CHAR,UID_ROOT,GID_WHEEL,0644,"hakios-touch");
 if(!primary){cdevsw_remove(major,&touch_cdevsw);printf("XCOVER5 M72 INPUT_FAILED devfs\n");return;}
 /* Old vendored injection ABI consumes the same 24-byte record. */
 if(!devfs_make_node(makedev(major,0),DEVFS_CHAR,UID_ROOT,GID_WHEEL,0644,"redwood-touch"))
  printf("XCOVER5 M72 INPUT_ALIAS_FAILED\n");
 printf("XCOVER5 M72 INPUT_READY virtual queue=512 record=24; physical backend pending\n");
}
