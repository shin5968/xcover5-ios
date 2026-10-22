#!/bin/bash
# Build a Samsung boot-only Odin package from a locally downloaded XNU kernel.
set -euo pipefail
cd "$(dirname "$0")/.."
KERNEL=${1:?usage: package_xnu.sh KERNEL NAME}
NAME=${2:?usage: package_xnu.sh KERNEL NAME}
[[ "$NAME" =~ ^[a-z0-9_-]+$ ]] || { echo "invalid output name" >&2; exit 2; }
KERNEL=$(realpath "$KERNEL")
mkdir -p shim/out odin
python3 tools/mkadt_xcover5.py "shim/out/$NAME.adt"
python3 tools/mkpayload.py "$KERNEL" "shim/out/$NAME.adt" "shim/out/payload-$NAME.bin" \
 --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress wdt=-1'
bash shim/build.sh 3 "$(pwd)/shim/out/payload-$NAME.bin"
cp shim/out/shim-boot.img "shim/out/shim-boot-$NAME.img"
python3 tools/make_odin_tar.py "shim/out/shim-boot-$NAME.img" "odin/AP_$NAME.tar.md5"
sha256sum "odin/AP_$NAME.tar.md5"
