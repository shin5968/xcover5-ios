#!/bin/bash
# CI-only: isolated RAM-root image, no phone or host physical disk writes.
set -euo pipefail
INIT=${1:?INIT required}
OUT=${2:?OUT required}
WORK=$(mktemp -d)
cleanup() { hdiutil detach "$WORK/mnt" >/dev/null 2>&1 || true; }
trap cleanup EXIT
hdiutil create -size 16m -layout NONE -fs 'Case-sensitive HFS+' -volname XCOVER5TEST "$WORK/root.dmg" >/dev/null
hdiutil attach -nobrowse -mountpoint "$WORK/mnt" "$WORK/root.dmg" >/dev/null
sudo mkdir -p "$WORK/mnt/sbin" "$WORK/mnt/dev" "$WORK/mnt/private/var"
sudo cp "$INIT" "$WORK/mnt/sbin/launchd"
sudo chmod 755 "$WORK/mnt/sbin/launchd"
echo 'XCOVER5 HFS root test' | sudo tee "$WORK/mnt/root-test.txt" >/dev/null
sync
hdiutil detach "$WORK/mnt" >/dev/null
hdiutil convert "$WORK/root.dmg" -format UDTO -o "$WORK/raw" >/dev/null
cp "$WORK/raw.cdr" "$OUT"
python3 - "$OUT" <<'PY'
import sys,struct
with open(sys.argv[1],'rb') as f:
 f.seek(1024);h=f.read(48)
assert h[:2] in (b'H+',b'HX'), 'not raw HFS+ at offset1024'
block,count=struct.unpack_from('>II',h,40)
assert block*count<=16*1024*1024
print('Raw HFS root verified:',sys.argv[1],block,count)
PY
