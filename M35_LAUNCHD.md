# M35 minimal Apple launchd handoff experiment

After M34 success, own PID1 updates only md0 RAM HFS root to writable, checks an8-byte /private/var write, closes/unlinks it, sets console descriptors and SETEXEC PLATFORM_IOS to original launchd. Preparation failure returns to init alive loop; PID1 never explicitly exits. After successful exec, launchd abort may panic the kernel; this is an experimental port. Recover with verified M34 boot-only image. eMMC/cache remain read-only.

Image includes native dyld symlink, locally injected original launchd/xpcproxy, temporary state directories and one RunAtLoad proof job. No stock aggregate job list. No Apple bytes in CI or git. Proof requires parentPID1 and ownPID>1, prints M35 JOB PASS, then exits0. This establishes only this job path, not bootstrap lookup, XPC services, SpringBoard or stability.

Stages351 remount;352 write/close/unlink;353 console;354 exec. No fallback after PID1 replacement. 11 mocked handoff cases,3 proof identity cases,14 M34 parent regressions and placeholder/hash/job checks pass. Hardware pending.
