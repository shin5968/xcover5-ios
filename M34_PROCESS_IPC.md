# M34: cross-process Mach request/reply

2026-10-24. Video151347 confirms M33 exit54, M31/M32 PASS.
M34 runs in its own probe task, temporarily sets THAT task's bootstrap port to
an allocated receive/send endpoint, and calls libSystem fork. XNU ipc_task_init
copies the parent's bootstrap send right into the child task. Parent immediately
restores its original bootstrap port and releases the extra saved right. PID1's
bootstrap and all unrelated tasks are unchanged.

The peer refreshes mach_task_self_ after fork, obtains its inherited bootstrap
send right via task_get_special_port and allocates a reply receive right in its
own namespace. Request uses COPY_SEND to bootstrap and MAKE_SEND_ONCE for the
reply right in the message header. Parent checks received send-once disposition,
message size/local port/non-complex/id/body and the exact forked PID. It replies
with MOVE_SEND_ONCE. Peer validates reply id/body and original parent PID,
destroys its reply receive right and releases the acquired bootstrap send right.
Parent checks waitpid of exact peer with exit55, then destroys its endpoint.

Both directions use 5000ms send/receive timeout options. Parent peer-wait is
bounded to50 attempts with100ms select delays. Failures with an unreaped child
kill only that PID and attempt nonblocking reap; late orphans are reaped by PID1.
The outer init retains its600-attempt timeout. A userspace retry bound cannot
bound a kernel syscall stuck internally. Partial task-owned rights are reclaimed
on task exit; no device storage is written.

Expected: M34 PEER PASS; M34 CHILD PASS cross-process request/reply + peer exit55;
M34 USER PASS cross-process Mach IPC + child exit55.
This demonstrates special-port inheritance and message-header send-once transfer,
not arbitrary service registration, bootstrap RPC server behavior or launchd.

Probe exit stages:
101 bindings/task;102 allocate;103 insert;104 get original bootstrap;105 set;
106 fork;107 restore;108 release saved right;109 receive;110 request validation;
111 reply send;112 peer wait/status/timeout;113 destroy parent receive port.
Peer:121 get bootstrap;122 allocate/PID;123 send;124 receive;125 reply validation;
126 destroy;127 deallocate bootstrap send right. Outer init stages251..254.

Validation:34 mocked parent/peer cases with distinct PID/task/port namespaces;
14 outer-parent cases;14 M33 parent and17 M31D regressions; independent Mach-O
binding/signature checks; iOS SDK layout/disposition static assertions. Mocks do
not execute true fork or kernel IPC. Hardware PASS in video153709 frame73: peer/child/user exit55 and init alive. Artifacts/m34 boot-only;
retain installed userdata cache. No agent phone writes.
