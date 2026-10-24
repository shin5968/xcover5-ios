# M29: original dyld against the installed iOS cache

M28 has passed on the device: read-only userdata HFS, 43 cache file sizes and head/tail CRCs. M29 is a boot-only diagnostic. Keep the installed userdata cache; do not reuse the ERASE_USERDATA package.

After M28 mount and inventory pass, PID 1 forks a child, connects console fds 0/1/2, and replaces that child with /emmc/sbin/m29-probe using posix_spawn SETEXEC and platform=2 (iOS). XNU 8796 spawn attribute offsets are checked by compiling assertions from its actual struct: platform108, copyin length184. The arguments descriptor is128bytes; all unused attributes are zero. The own Mach-O probe is iOS16 LC_MAIN, using the same locally injected, unchanged original Apple dyld. DYLD_SHARED_CACHE_DIR names the mounted volume; Apple security policy may filter this variable, but the mount also matches the iOS default path. No kernel execution policy changes.

Successful child main checks argc/argv, PID>1, shared_region_check_np and the mapped dyld cache magic, reads the eMMC proof, and exits50. Parent accepts only the exact child's status0x3200. Stages201/202/203/204 report fork/wait/unexpected status/timeout; console setup/spawn errors exit127. Parent waits up to600 nonblocking polls with100ms sleeps then kills only that child and keeps init alive. Kernel syscall stalls are not bounded by this userspace polling limit.

Expected: M29 CHILD PASS: Apple dyld main + shared cache + eMMC file read; M29 USER PASS: iOS dyld cache/main + child exit50. Runtime failures must be reported verbatim. This does not establish real launchd, SpringBoard or general application compatibility. The 25 focused instruction tests simulate syscalls and main entry; they do not execute Apple dyld or validate cache loading on hardware.

Public CI ships a non-executable placeholder only. Apple dyld is injected locally with its existing full SHA256 check. Original cache files are neither changed nor uploaded. Synthetic3GiB cache-template generation is now an explicit workflow input, disabled for ordinary boot-only builds.
