# M31: heap allocation and pthread callback

The M30 import layout is reused with malloc, free, pthread_create,
pthread_join and pthread_self. M30 output remains byte-identical.

The child allocates4096 bytes, fills bytes32..4095 with0x5a and starts one
joinable pthread with the heap as context. The worker verifies its pthread
identity differs from the main thread, verifies the entire pattern, replaces
it with0xa5, sets a completion flag and returns the context pointer. Main
joins, checks the returned pointer, flag and all4064 changed bytes, then
calls free. Join establishes visibility; there is no unsynchronized polling.
The assembly callback preserves x19/x20/x29/LR and keeps its stack16-aligned.

Expected hardware success:
`M31 CHILD PASS: malloc + distinct pthread + shared heap + join + free`
and `M31 USER PASS: malloc/pthread/join/free + child exit 52`.

Child exits101..107 identify missing import, malloc failure, null main
pthread identity, create failure, invalid handle/join failure, callback
result/identity/content failure, final data mismatch. Parent stages221..224
identify fork/wait/bad child status/timeout. The parent waits for its exact
child up to600 polling intervals of100ms and kills only that child on timeout.
A syscall that itself blocks is not bounded by this polling mechanism.

There are console markers before malloc, before pthread_create and inside
the worker. Crash/timeout after the last marker requires device diagnostics;
this build does not claim to fix unsupported pthread operations in advance.
No media writes or kernel/Apple runtime modifications are introduced.

Validation: independent Mach-O bind/symbol/signature checks; eleven mocked
allocation/thread instruction paths with a separate worker register context
and stack, shared heap, callback callee-save checks and injected failures;
fourteen parent spawn/wait paths; M30 byte reproduction and ten M30 mocked
import paths. These mocks do not validate Apple's scheduler/runtime. Hardware
result pending. Package boot only in xcover5/artifacts/m31; retain userdata.

## Hardware result 2026-10-24 14:11

Photo141145 confirms worker entry, M31 CHILD PASS and USER PASS exit52; M29 and M30 also pass. Original libSystem malloc/free and pthread create/join with a distinct worker and checked shared heap are established.

## M31D diagnostics after M32 hardware run (2026-10-24)

Photo 143016 shows M32 CHILD/USER PASS (counter 2048, exit 53), but M31 stage 224 with zero status. M31 passed in photo 141145; do not treat the combined suite as stable. Stage 224 is the parent's bounded retry timeout; zero is a placeholder, not a successful child exit. No M31 main-entry message is visible in the failing run.

M31D changes only the PID1 harness. M31 and all other probe binaries stay unchanged. M31 alone requests DYLD_PRINT_LIBRARIES and DYLD_PRINT_INITIALIZERS; Apple dyld's existing policy decides whether to honor these variables. No policy bypass or kernel change is added.

The parent records raw monotonic absolute ticks through XNU syscall 116's third argument, with both clock call errors, PID, retries remaining, select error count/last errno and timeout kill error. Each tick value is printed as separate hexadecimal high and low 32-bit words. Clock errors invalidate their timestamp. The existing 600-attempt wait behavior remains: this diagnostic does not claim a fixed elapsed-time deadline or a hang fix. The live init loop still reaps late children.

Local test_m31_diagnostics.py executes assembled parent instructions using mocked syscalls across 17 cases, including clock/select/kill errors, exact-PID wait status, SETEXEC environment and child setup failures. This is not a real dyld/scheduler test. Boot-only artifact target: xcover5/artifacts/m31d. Preserve installed userdata cache.
