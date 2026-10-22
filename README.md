# XCover5 single-core XNU early boot

Target: Apple xnu-8796.141.3, tag commit 1b191cb58250d0705d8a51287127505aa4bc0789.
Build-support: blacktop/darwin-xnu-build commit 663906528d1cd5ea8fde7de6f16de73db9511549.
Base patches 0001-0018 are copied from the local ios-sweet checkout; 0019 is the XCover5 overlay. Keep MACHINE_CONFIG=SWEET to reuse the early kernel infrastructure; this is an Exynos-only fork, not a multi-board patch series.

Implemented: GICv2 MMIO acknowledge/EOI, timer IRQ27, self-SGI1, single CPU, framebuffer 0xfa000000 at 720x1480 stride 2880, ADT generator at ../tools/mkadt_xcover5.py. Full kernel compilation/runtime verification is pending.

Initial RAM candidate: 0xa0000000..0xafffffff, a reservation-free interval in collected live iomem. Last 1MiB is panic log. Confirm against live FDT and initrd at each actual kernel load; do not assume all 4GB is available. No UFS/eMMC or other Qualcomm hardware drivers are in this 19-patch subset.

First target is early kernel console, not iOS GUI. Missing later providers (libpthread, crypto, root filesystem) can cause a later unresolved-symbol/build/boot failure; report those before adding more base patches. Never stage the full ios-sweet series: its later hardware MMIO is wrong for Exynos.

GitHub Actions workflow: .github/workflows/xnu.yml. Pushes changing kernel patches or the workflow trigger a DEVELOPMENT/SWEET build. The initial target is kernel console output; no boot or userdata partition is flashed by CI.

Source provenance: tools/adt.py, tools/mkpayload.py and tools/sweet_adt_base.py are copies of ios-sweet equivalents (the last renamed from mkadt.py). Source trees/build-support are downloaded reference/build inputs, not authored code.
