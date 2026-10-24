# M35 minimal Apple launchd handoff experiment

After M34 success, own PID1 updates only md0 RAM HFS root to writable, checks an8-byte /private/var write, closes/unlinks it, sets console descriptors and SETEXEC PLATFORM_IOS to original launchd. Preparation failure returns to init alive loop; PID1 never explicitly exits. After successful exec, launchd abort may panic the kernel; this is an experimental port. Recover with verified M34 boot-only image. eMMC/cache remain read-only.

Image includes native dyld symlink, locally injected original launchd/xpcproxy, temporary state directories and one RunAtLoad proof job. No stock aggregate job list. No Apple bytes in CI or git. Proof requires parentPID1 and ownPID>1, prints M35 JOB PASS, then exits0. This establishes only this job path, not bootstrap lookup, XPC services, SpringBoard or stability.

Stages351 remount;352 write/close/unlink;353 console;354 exec. No fallback after PID1 replacement. 11 mocked handoff cases,3 proof identity cases,14 M34 parent regressions and placeholder/hash/job checks pass. Hardware video161303: Apple launchd PID1/libignition reached, then username mobile resolution failed and PID1 exited; no JOB PASS. M30 separately timed out before main.

## M35A account files

Add owned locked-password root/mobile/nobody records, /etc -> private/etc, passwd/group0644 and master.passwd0600, mobile home501:501 mode0700. Kernel, init, probes and Apple binaries remain identical to M35. This targets the observed missing mobile identity only; runtime lookup and proof job require hardware verification. M30 intermittent timeout remains unresolved.

## M35B persistent HFS ownership

Video174106: launchd passed account initialization and rejected proof plist with error122. Raw catalog confirms plist, ancestors and executable uid501/gid20 despite sudo staging. Enable owners when mounting CI image, assign all paths root0:0 after staging, retain mobile home501:501, and explicitly set job0644. Validate raw catalog ownership for every file/folder and launchd path modes after unmount. Prior host mode-only checks missed ownership; this check reads persisted metadata. Runtime JOB PASS remains pending.

## M35C xpcproxy exit diagnostics

Video175340 confirms job registration and PID17 xpcproxy SIGKILL in user/501 domain, no proof PASS. Add SWEET kernel logs for executable vnode name/load result/uid and committed exit namespace/code/flags/csflags for early PIDs1..64. Execution, signature and signal policy unchanged. Userspace image staging unchanged from M35B. This is a diagnostic build; root cause and JOB PASS remain pending.

## M35D signing-invalidity details

Photo183617: xpcproxy uid0 rv9 cs0x01000001 (CS_KILLED|CS_VALID), no committed reason. Add SIGN diagnostic with image vnode/errno/spawn/vfexec/signature-failure namespace/code, and PAGE diagnostic with virtual address/prior csflags/force flags. Enable existing page-invalidity detail log on SWEET; no page-validation, entitlement or exec policy change. Package M35D retains M35E SIGN/PAGE marker names to distinguish from M35D LOAD/EXIT. Hardware diagnosis pending.

## M35E exec-stage diagnostics

Video185413: M34 PASS, launchd PID1 load/platform accepted, then no libignition through243s. Add begin/end markers around process-signature, thread-signature and posix_spawn final return-wait clear. Marker prefix M35F distinguishes stage logs from existing LOAD/EXIT and SIGN/PAGE. No scheduling, signature or exec behavior change. Exact stall cause remains unknown.

## M35F fast diagnostic route

Skip M21-M26 and M28inventory/M29-M33 regression executions at boot; retain M18/M19/M20 storage checks, M28 cache mount and M34 success gate before M35. Print explicit FAST notice so skipped probes are not mistaken for new PASS evidence. All probe files and kernel diagnostics remain available and unchanged. This avoids earlier-probe 60second timeout waits and repeated cache logging; it does not solve pre-main stalls in M34/launchd or xpcproxy SIGKILL. PID numbers differ.
