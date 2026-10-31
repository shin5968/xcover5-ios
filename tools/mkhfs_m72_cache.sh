#!/bin/bash
set -euo pipefail
OUT=${1:?output required}
test ! -e "$OUT"
WORK=$(mktemp -d)
trap 'hdiutil detach "$WORK/mnt" >/dev/null 2>&1 || true' EXIT
hdiutil create -size 3g -layout NONE -fs 'Case-sensitive HFS+' -volname XCIOSCACHE "$WORK/cache.dmg" >/dev/null
hdiutil attach -owners on -nobrowse -mountpoint "$WORK/mnt" "$WORK/cache.dmg" >/dev/null
sudo python3 tools/cache_placeholders.py "$WORK/mnt"
sudo python3 tools/stage_m66_icu.py cache "$WORK/mnt"
printf 'XCOVER5 M28 userdata cache volume verified\n' | sudo tee "$WORK/mnt/m28-cache-proof.txt" >/dev/null
sudo chmod 444 "$WORK/mnt"/*
sudo python3 tools/stage_m72_cache_resources.py cache "$WORK/mnt"
sudo chown -R 0:0 "$WORK/mnt"
sync
hdiutil detach "$WORK/mnt" >/dev/null
hdiutil convert "$WORK/cache.dmg" -format UDTO -o "$WORK/raw" >/dev/null
cp "$WORK/raw.cdr" "$OUT"
python3 tools/fix_cache_ownership.py "$OUT" > "$OUT.ownership.json"
python3 - "$OUT" <<'PY'
import struct,sys
from pathlib import Path
p=Path(sys.argv[1]);assert p.stat().st_size==3*1024**3
with p.open('rb') as f:f.seek(1024);h=f.read(512)
block,total,free=struct.unpack_from('>III',h,40)
assert h[:4]==b'HX\0\5' and (block,total)==(4096,786432) and free*block>=16*1024**2
print('M72 same 3GiB geometry; cache free bytes',free*block)
PY
