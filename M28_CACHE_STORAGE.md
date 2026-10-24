# M28: internal cache storage test

This build tests a dedicated read-only HFSX cache volume in the existing `userdata` partition.
It does not establish successful iOS launch, libSystem initialization, or dyld shared-cache mapping.

## Destructive installation scope

The locally generated `AP_M28_ERASE_USERDATA_CACHE.tar.md5` contains exactly:

- `boot.img`: the M28 test kernel, shim and 16 MiB RAM root.
- `userdata.img`: a 3 GiB HFSX volume containing 43 locally supplied original cache files.

Flashing this archive **destroys the existing Android userdata filesystem and access to its apps,
photos and files**. This is not a secure erase of every old byte. No PIT, GPT, `super`, bootloader,
modem, or other partition is included. Do not enable Odin Re-Partition. Use the combined archive
in AP so both images are installed together; do not boot Android between these writes.

The user explicitly accepted Android userdata loss and selected internal storage only.
No phone writes are performed by these scripts. The user performs the Odin flash.

## Verification boundary

The kernel discovers `userdata` by its GPT name, checks header/table CRC and partition overlap,
and bounds the block device to the 3 GiB volume. It rejects writes, dirty and journaled volumes.
PID 1 mounts `/dev/xcuserdata` read-only at `/System/Library/Caches/com.apple.dyld`, checks the
volume proof file, and runs `/emmc/sbin/m28-probe`.

The child checks all 43 file lengths, header magic, and first/last 4096-byte CRCs; exit 49 is the
expected test result. These sampled runtime CRCs are not a whole-file integrity check.
Before packaging, local injection validates every original file's SHA256, verifies that only
placeholder extents changed, and independently extracts the HFS files to recheck full SHA256.

The CI image contains synthetic placeholders only. Original Apple bytes stay local and are
not committed or uploaded to GitHub. The boot-only package cannot install this cache volume.

Expected device lines:

```
XCOVER5 M28 USER PASS: userdata cache volume proof
XCOVER5 M28 CHILD PASS: 43 cache files size + head/tail CRC verified
XCOVER5 M28 USER PASS: cache inventory + child exit 49
XCOVER5 init: still alive
```

M27's known-failing launch is skipped in this storage test. Actual cache loading remains the next
separate test, including executable/cache platform compatibility and shared-region behavior.
