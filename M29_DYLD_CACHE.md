# M29: original dyld against the installed iOS cache

M28 has passed on the device: read-only userdata HFS, 43 cache file sizes and head/tail CRCs. The initial M29 was a boot-only diagnostic. The M29B ownership repair below requires rewriting the userdata cache image while reusing that same M29 boot image.

After M28 mount and inventory pass, PID 1 forks a child, connects console fds 0/1/2, and replaces that child with /emmc/sbin/m29-probe using posix_spawn SETEXEC and platform=2 (iOS). XNU 8796 spawn attribute offsets are checked by compiling assertions from its actual struct: platform108, copyin length184. The arguments descriptor is128bytes; all unused attributes are zero. The own Mach-O probe is iOS16 LC_MAIN, using the same locally injected, unchanged original Apple dyld. DYLD_SHARED_CACHE_DIR names the mounted volume; Apple security policy may filter this variable, but the mount also matches the iOS default path. No kernel execution policy changes.

Successful child main checks argc/argv, PID>1, shared_region_check_np and the mapped dyld cache magic, reads the eMMC proof, and exits50. Parent accepts only the exact child's status0x3200. Stages201/202/203/204 report fork/wait/unexpected status/timeout; console setup/spawn errors exit127. Parent waits up to600 nonblocking polls with100ms sleeps then kills only that child and keeps init alive. Kernel syscall stalls are not bounded by this userspace polling limit.

Expected: M29 CHILD PASS: Apple dyld main + shared cache + eMMC file read; M29 USER PASS: iOS dyld cache/main + child exit50. Runtime failures must be reported verbatim. This does not establish real launchd, SpringBoard or general application compatibility. The 25 focused instruction tests simulate syscalls and main entry; they do not execute Apple dyld or validate cache loading on hardware.

Public CI ships a non-executable placeholder only. Apple dyld is injected locally with its existing full SHA256 check. Original cache files are neither changed nor uploaded. Synthetic3GiB cache-template generation is now an explicit workflow input, disabled for ordinary boot-only builds.

## M29B: root-owned cache image

Device evidence on 2026-10-24: iOS platform spawning was allowed and original dyld found the installed cache. Cache mapping reported `not in trust cache`, then `owned by uid=501 instead of 0`. In this kernel's vm_unix.c fallback, the latter rejects the mapping with EPERM. M29 failed at stage203/status6; PID1 remained alive. Cache mapping and libSystem/main are still unproven.

The raw HFS catalog independently confirmed uid501/gid20 for 43 cache files, the proof file and the volume root. `fix_cache_ownership.py` pins the exact previously verified source image SHA256, copies into a new regular file and changes only those 45 UID/GID fields to zero. A complete byte comparison verified only135 changed bytes; all other bytes are identical. Two existing private directories were already root-owned. Independent 7-Zip extraction verified the complete SHA256 of all43 cache files and the volume proof after repair.

Fixed raw image SHA256: `0c170b631be57a45d47c32239e7ce0614bdb7dc998c12d419c5055c6a2c20feb`.

The template builder now enables mount ownership, explicitly assigns root ownership, and checks both mounted stat results and raw on-disk catalog records. The macOS template creation path requires a subsequent macOS run; the local repair uses the existing verified image. No kernel trust/ownership checks are weakened. No Apple binary contents change.

Local output: `AP_M29B_ROOT_CACHE_ERASE_USERDATA.tar.md5`, containing only the unchanged M29 `boot.img` and corrected sparse-LZ4 `userdata.img.lz4`. This overwrites Android userdata when manually flashed. No PIT or repartition operation. Reusing the previous boot-only archive cannot fix the installed cache's ownership. Hardware validation is pending: confirm the uid501 rejection disappears, then capture any subsequent error or M29 CHILD/USER PASS (exit50). This repair does not imply iOS UI boot completion.

## M29D: terminal user-abort diagnostics

After the M29B ownership repair, the device reaches subcache42 without the uid501 error, then M29 exits with wait status0x0b (SIGSEGV). This does not prove successful cache mapping or main entry. The remaining not-in-trust-cache messages alone do not identify the crash.

Patch0039 adds SWEET-only logging in handle_user_abort after recoverable VM faults have returned and immediately before existing exception delivery. It records PID, ESR, fault status/protection, Mach error, PC, FAR, LR, SP, FP, CPSR and X0-X7. It reads saved registers only, without reading user memory, changing state, retrying the fault, or weakening code-signing/ownership checks. Alignment and other exception paths outside this handler are not universally covered.

This diagnostic uses the unchanged M29 userspace/root image and the installed root-owned cache. The boot-only AP must contain exactly boot.img; do not rewrite userdata. Hardware evidence required: the M29D ABORT/PC/LR lines and subsequent status. It is a diagnostic build, not a SIGSEGV fix or a new iOS execution milestone.
