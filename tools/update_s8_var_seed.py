"""Update only preference blobs in an already staged M74 RAMFS template."""
from pathlib import Path
import json, os, plistlib, sys
from stage_m63_resources import safe_path, CONFIG
from stage_m74_var import SEED

def update(root):
    root = Path(root)
    seed = safe_path(root, SEED)
    manifest = safe_path(root, SEED+'/manifest.tsv')
    rows = [line.split('\t') for line in manifest.read_text().splitlines()]
    paths = {row[4]:row for row in rows}
    assert len(paths) == len(rows) and len(rows) < 500
    slots = {row[5] for row in rows if row[0] == 'f'}
    changed = []
    for source in sorted((CONFIG/'seed-preferences').glob('*.plist')):
        name = '/private/var/mobile/Library/Preferences/'+source.name
        data = source.read_bytes(); assert isinstance(plistlib.loads(data), dict)
        if name in paths:
            row = paths[name]
            assert row[0] == 'f' and row[1:3] == ['501','501']
            assert len(row[5]) == 8 and row[5][:4].isdigit() and row[5].endswith('.bin')
        else:
            slot = next(f'{i:04}.bin' for i in range(9999) if f'{i:04}.bin' not in slots)
            assert not (seed/'files'/slot).exists()
            slots.add(slot)
            row = ['f','501','501','600',name,slot]; rows.append(row)
        row[3] = '600'
        blob = safe_path(root, SEED+'/files/'+row[5])
        blob.write_bytes(data); blob.chmod(0o644); os.chown(blob,0,0)
        changed.append(name)
    output = ''.join('\t'.join(row)+'\n' for row in rows).encode()
    assert len(output) < 65536 and len(rows) <= 512
    manifest.write_bytes(output); manifest.chmod(0o644); os.chown(manifest,0,0)
    return dict(preferences=changed, records=len(rows))

if __name__ == '__main__':
    print(json.dumps(update(Path(sys.argv[1])), indent=2))
