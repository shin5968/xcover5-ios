#!/bin/bash
# Build the XCover5 shim and wrap it in a Samsung-compatible boot.img v2
# (header values copied from the stock boot.img of G525NKXSFEYL1).
# Run inside WSL/Linux: needs aarch64-linux-gnu-gcc and python3.
set -euo pipefail
TEST=${1:-1}
[[ "$TEST" == 1 || "$TEST" == 2 || "$TEST" == 3 || "$TEST" == 4 || "$TEST" == 5 ]] || { echo "usage: build.sh [1|2|3|4|5] [XNU_PAYLOAD]" >&2; exit 2; }
cd "$(dirname "$0")"
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
CFLAGS="-DSHIM_TEST=$TEST -O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c mmcprobe.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done
abs=$(aarch64-linux-gnu-readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/mmcprobe.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/mmcprobe.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
size=$(aarch64-linux-gnu-nm out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image
if [[ "$TEST" == 3 ]]; then
    [[ -n "${2:-}" && -f "$2" ]] || { echo "XNU payload required" >&2; exit 2; }
    python3 ../tools/mkbootimg_v2.py out/Image ../stock/unpacked/dtb out/shim-boot.img --ramdisk "$2"
else
    python3 ../tools/mkbootimg_v2.py out/Image ../stock/unpacked/dtb out/shim-boot.img
fi
ls -l out/Image out/shim-boot.img
