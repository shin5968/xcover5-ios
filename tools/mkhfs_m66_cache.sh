#!/bin/bash
# Synthetic local FILE only; never original iOS data or a physical device.
set -euo pipefail
OUT=${1:?output required}
test ! -e "$OUT"
WORK=$(mktemp -d)
cleanup() { hdiutil detach "$WORK/mnt" >/dev/null 2>&1 || true; }
trap cleanup EXIT
hdiutil create -size 3g -layout NONE -fs 'Case-sensitive HFS+' -volname XCIOSCACHE "$WORK/cache.dmg" >/dev/null
hdiutil attach -owners on -nobrowse -mountpoint "$WORK/mnt" "$WORK/cache.dmg" >/dev/null
sudo python3 tools/cache_placeholders.py "$WORK/mnt"
sudo python3 tools/stage_m66_icu.py cache "$WORK/mnt"
printf 'XCOVER5 M28 userdata cache volume verified\n' | sudo tee "$WORK/mnt/m28-cache-proof.txt" >/dev/null
sudo chmod 444 "$WORK/mnt"/*
sudo chown -R 0:0 "$WORK/mnt"
sync
hdiutil detach "$WORK/mnt" >/dev/null
hdiutil convert "$WORK/cache.dmg" -format UDTO -o "$WORK/raw" >/dev/null
cp "$WORK/raw.cdr" "$OUT"
python3 tools/fix_cache_ownership.py "$OUT" > "$OUT.ownership.json"
python3 - "$OUT" "$OUT.ownership.json" <<'PY'
import json,struct,sys
from pathlib import Path
sys.path.insert(0, 'tools')
from stage_m66_icu import FILES
p=Path(sys.argv[1]);assert p.stat().st_size==3*1024**3
with p.open('rb') as f:f.seek(1024);h=f.read(48)
assert h[:4]==b'HX\0\5' and struct.unpack_from('>II',h,40)==(4096,786432)
rows=json.loads(Path(sys.argv[2]).read_text())
assert all(r['uid']==r['gid']==0 for r in rows)
assert set(FILES)<=set(r['name'] for r in rows)
print('M66 synthetic 43 cache + 2 ICU file volume, root ownership PASS')
PY
