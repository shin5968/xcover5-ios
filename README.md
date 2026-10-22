# XCover5 single-core XNU early boot

Target: Apple xnu-8796.141.3, tag commit 1b191cb58250d0705d8a51287127505aa4bc0789.
Build-support: blacktop/darwin-xnu-build commit 663906528d1cd5ea8fde7de6f16de73db9511549.
Base patches 0001-0018 are copied from the local ios-sweet checkout; 0019 is the XCover5 overlay. Keep MACHINE_CONFIG=SWEET to reuse the early kernel infrastructure; this is an Exynos-only fork, not a multi-board patch series.

Implemented: GICv2 MMIO acknowledge/EOI, timer IRQ27, self-SGI1, single CPU, framebuffer 0xfa000000 at 720x1480 stride 2880, ADT generator at ../tools/mkadt_xcover5.py. Full kernel compilation/runtime verification is pending.

Initial RAM candidate: 0xa0000000..0xafffffff, a reservation-free interval in collected live iomem. Last 1MiB is panic log. Confirm against live FDT and initrd at each actual kernel load; do not assume all 4GB is available. No UFS/eMMC or other Qualcomm hardware drivers are in this 19-patch subset.

First target is early kernel console, not iOS GUI. Missing later providers (libpthread, crypto, root filesystem) can cause a later unresolved-symbol/build/boot failure; report those before adding more base patches. Never stage the full ios-sweet series: its later hardware MMIO is wrong for Exynos.

GitHub Actions workflow: .github/workflows/xnu.yml. Pushes changing kernel patches or the workflow trigger a DEVELOPMENT/SWEET build. The initial target is kernel console output; no boot or userdata partition is flashed by CI.

Source provenance: tools/adt.py, tools/mkpayload.py and tools/sweet_adt_base.py are copies of ios-sweet equivalents (the last renamed from mkadt.py). Source trees/build-support are downloaded reference/build inputs, not authored code.

## Samsung boot shim

`shim/build.sh 3 /absolute/path/to/payload.bin` builds the XNU loader using aarch64-linux-gnu-gcc on Linux/WSL. Supply the device DTB locally at `stock/unpacked/dtb`; device dumps are excluded from git. Loader source compiles with -Wall -Wextra -Werror. It bounds payload segments, ADT and boot arguments and accepts only the selected 255MiB RAM window; actual kernel handoff is untested.

M9 bare-metal runtime validation: 16KiB MMU, virtual timer IRQ27 and physical IRQ30 each delivered 29 interrupts in 300ms. SMP is unresolved. Existing M9 images are preserved outside this repository. Kernel build and boot results must be reported separately.

## 2026-10-22 device results and current build

The first kernel reached IOKit but SHA1Init panicked because the crypto provider was absent. An early ADT omitting optional chip identity passed this point. Matching SweetCPU via its compatibility alias then registered CPU0 and passed the SGI self-test. The next observed panic is `pthread kernel extension not loaded` at pthread_shims.c:318.

The current patch set therefore includes the pinned public libpthread provider, portable BearSSL AES/MD5/SHA1/SHA384/SHA512 and built-in SHA256. These are hardware-independent base patches; no Qualcomm UFS/USB/touch patches are included. Build results and device results are separate: CPU+SGI runtime success is verified; the added providers await a new boot test.

To package a downloaded kernel locally: `bash tools/package_xnu.sh /absolute/kernel.development.sweet xnu-next`. This creates `odin/AP_xnu-next.tar.md5` containing boot.img only. Supply stock/unpacked/dtb locally. This repository contains no device dumps or Apple firmware/userland.
