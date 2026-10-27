/* Owned interposing dylib; calibration call site is in main. */
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "m39s-reply-observer.h"
void m39s_activate(void) { atomic_store_explicit(&m39s_active,1,memory_order_relaxed); }
unsigned m39s_calibration_count(void) { return atomic_load(&m39s_calibration_hits); }
void m39s_dump(void) { m39s_snapshot_dump(); }
