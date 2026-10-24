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
