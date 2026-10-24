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

## M29E: describe the no-import probe to Apple dyld

Device M29D: entry0x1009f11b0, PC0x100a37238, LR0x100a37230, FAR0x48, ESR0x92000006, protection1, Mach code1, final wait status0x0b. Original dyld has unslid entry0x151b0, giving slide0x1009dc000 and fault file offset0x5b238. Offline GNU AArch64 disassembly identifies `ldr w2, [x8, #72]`, immediately preceded by `ldr x8, [x22, #32]`. Native symbol table places this in MachOAnalyzer::forEachRebase_Relocations at0x5b1c8. The matching reference source reads leInfo.dynSymTab->locreloff there; LinkEditInfo.dynSymTab is offset32 and locreloff is offset72. The FAR therefore identifies a null dynSymTab for this dereference. These are offline binary/source correlations with the photographed runtime registers; REA opened the artifact but its decompiler provider was unavailable.

The own M29 probe omitted LC_DYLD_INFO_ONLY and LC_DYSYMTAB, selecting the classic-relocation fallback. M29E explicitly describes empty rebase/bind/export streams (LC_DYLD_INFO_ONLY), an empty LC_SYMTAB with one-byte NUL string table, and empty LC_DYSYMTAB. The 16-byte linkedit prefix is signed and the CodeDirectory is regenerated, including its new partial page. This is opt-in only for M29; legacy M22/M27 binaries remain byte-identical. M29 executable instructions and PC-relative data remain byte-identical. Apple dyld/cache bytes and all kernel policies are unchanged.

`test_m29_metadata.py` verifies legacy reproduction, unchanged code, load-command bounds, empty streams/symbol ranges, linkedit containment and every CodeDirectory page digest. Device success remains pending; this fixes the identified malformed metadata, not a claim of completed libSystem/main or iOS UI. Reuse installed root-owned userdata cache. Save all new outputs under the project xcover5 directory per user preference.


## M29E hardware result (2026-10-24 13:34)

User photos 133438/133440/133442 confirm M29 CHILD PASS (Apple dyld main + shared cache + eMMC file read) and USER PASS, child exit50. The not-in-trust-cache diagnostics remain but are not fatal for this path. This establishes the no-import probe, not explicit libSystem calls or iOS UI.
