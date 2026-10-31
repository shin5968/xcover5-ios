#!/bin/bash
# dxb invokes staging scripts in its XNU source tree, before applying patches.
set -euo pipefail
[[ "${MACHINE_CONFIG:-}" == SWEET ]] || exit 0
[[ "${MACOS_VERSION:-}" == 13.5 ]] || exit 1
python3 - <<'PY2'
from pathlib import Path
import hashlib,json,shutil
source=Path('../../third_party/hackios-portable')
manifest=json.loads((source/'ORIGIN.json').read_text())
for item in manifest['files']:
 p=source/item['path'];data=p.read_bytes()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],p
for name in ('apfs','ramfs'):
 target=Path('bsd/miscfs')/name
 assert not target.exists(),target
 shutil.copytree(source/'xnu/files/bsd/miscfs'/name,target)
print('M72 pinned HackiOS APFS/ramfs source identity PASS')
PY2
