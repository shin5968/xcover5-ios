# M33: Mach port messaging between two threads

2026-10-24. M31D video plus user-reported three repeat boots passed M31/M32.
The original intermittent M31 timeout cause remains unresolved; retain M31D.

M33 is a foundational Mach message test within ONE task. It does not establish
cross-process right transfer, bootstrap services, launchd or GUI functionality.
Main imports the data symbol mach_task_self_ (dereferenced, never called),
allocates a receive right, creates a send right with MAKE_SEND, and starts a
receiver pthread. Main sends a 32-byte non-complex inline message using
COPY_SEND. The worker receives on that port into 128 bytes (including trailer
space), checks size/local port/non-complex/id/two payload words and returns
the context pointer. Main checks pthread_join/result and destroys the port.
A main-sends-first or worker-receives-first scheduling order is valid.

Both mach_msg calls specify a 5000ms timeout. Parent has the existing 600
100ms wait-attempt bound, followed by child-only SIGKILL and later init reap.
This retry bound does not bound a stuck syscall itself. Failed probe exits
terminate the task/threads, reclaiming remaining task-owned port rights.

Expected:
M33 CHILD PASS: Mach port + thread send/receive + id/body + destroy
M33 USER PASS: Mach port/thread IPC + child exit 54

Exit codes:101 missing binding/task name,102 allocate/name,103 insert send
right,104 pthread_create/handle,105 send,106 join,107 receive/result/message
validation,108 destroy. Parent stages241/242/243/244=fork/wait/status/timeout.
Capture the last CHILD line, USER status and any M29D terminal abort on failure.

Local validation: independent Mach-O bind/symbol/signature decoding;18 mocked
API instruction cases including receive timeout and every message field;
14 M33 parent paths;17 M31D parent regressions. Mock worker runs at join on a
separate stack/register context, not real IPC or concurrent scheduling.
iOS SDK static assertions check header layout, port width and options/rights.
Hardware result pending.

Outputs: xcover5/artifacts/m33. Boot-only AP; retain installed userdata cache.
No Apple runtime modification. No device flashing performed by the agent.

Hardware video151347 confirms M33 CHILD/USER PASS exit54 and M31/M32 PASS.
