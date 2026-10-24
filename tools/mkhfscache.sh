#!/bin/bash
# Creates an isolated LOCAL FILE, never formats a physical device.
# CI includes synthetic placeholders only; original cache is injected locally.
set -euo pipefail
OUT=${1:?output required}
WORK=$(mktemp -d)
cleanup() { hdiutil detach "$WORK/mnt" >/dev/null 2>&1 || true; }
trap cleanup EXIT
hdiutil create -size 3g -layout NONE -fs 'Case-sensitive HFS+' -volname XCIOSCACHE "$WORK/cache.dmg" >/dev/null
hdiutil attach -nobrowse -mountpoint "$WORK/mnt" "$WORK/cache.dmg" >/dev/null
sudo python3 tools/cache_placeholders.py "$WORK/mnt"
printf 'XCOVER5 M28 userdata cache volume verified\n' | sudo tee "$WORK/mnt/m28-cache-proof.txt" >/dev/null
sudo chmod 444 "$WORK/mnt"/dyld_shared_cache_arm64* "$WORK/mnt/m28-cache-proof.txt"
sync
hdiutil detach "$WORK/mnt" >/dev/null
hdiutil convert "$WORK/cache.dmg" -format UDTO -o "$WORK/raw" >/dev/null
cp "$WORK/raw.cdr" "$OUT"
python3 - "$OUT" <<'PY'
import os,sys,struct
assert os.path.getsize(sys.argv[1]) == 3*1024**3
with open(sys.argv[1],'rb') as f:
 f.seek(1024);h=f.read(512)
assert h[:4]==b'HX\0\5'
assert struct.unpack_from('>II',h,40)==(4096,786432)
assert struct.unpack_from('>I',h,4)[0] & 0x2900 == 0x100
print('3GiB clean non-journaled HFSX template verified')
PY
