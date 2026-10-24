# M32 mutex-protected shared counter

Two joinable pthread workers each perform1024 iterations of
pthread_mutex_lock, counter increment, and pthread_mutex_unlock. Both return
codes are checked on every iteration. Main checks distinct non-null pthread
handles, joins both, checks both callback results and counter2048, then
checks pthread_mutex_destroy succeeds. No files or device media are written.

The mutex has128 bytes of16-byte-aligned storage at DATA+0x100, separate from
the import table. CI compiles static assertions against the iOS SDK to check
opaque mutex size/alignment and pthread_t/pointer width. Standard bindings
import six libSystem functions; the generalized image builder reproduces
M30 and M31 byte-for-byte. Callback assembly preserves callee-saved registers.

Expected hardware result:
`M32 CHILD PASS: two pthreads + mutex counter 2048 + joins + destroy`
and `M32 USER PASS: mutex/two workers/counter + child exit 53`.

Child exits101 missing import,102 mutex init,103/104 worker create,
105 invalid/non-distinct handles,106/107 join,108 worker result (including
lock/unlock failure),109 counter mismatch,110 mutex destroy. Errors during
partial setup terminate this diagnostic child process and its threads; PID1
continues. Parent stages231..234 cover fork/wait/status/timeout and retain the
existing bounded polling and child-only kill behavior. A blocking syscall
itself is not bounded by the parent userspace polling loop.

Local validation decodes Mach-O bindings, symbols, protections and signature;
14 mocked pthread/mutex instruction scenarios check each increment occurs
while the mock lock is held,2048 balanced cycles, callback ABI and injected
failures. Workers execute serially in that harness, so it does not validate
actual lock contention or the Apple scheduler.14 parent wait/spawn scenarios
and M31 instruction regressions also pass. Real scheduling order is not
assumed by the device test, and a pass does not prove contention occurred.
Hardware M32 result pending. No kernel or Apple runtime modifications.

Outputs: xcover5/artifacts/m32, boot-only AP. Keep existing userdata cache.

## Hardware result (2026-10-24)
Photo 143016 confirms M32 CHILD/USER PASS: two workers, mutex counter 2048, joins, destroy, exit 53. The same run shows M31 timeout stage 224 before a visible main-entry marker. M31D investigates that intermittent failure before adding another milestone. A successful counter test does not prove blocking contention occurred.
