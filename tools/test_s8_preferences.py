"""Check S8-derived preferences survive the real RAMFS seed generation."""
from pathlib import Path
import os, plistlib, tempfile
from stage_m63_resources import apply_var
from stage_m74_var import stage, SEED

assert os.geteuid() == 0, 'Run as root to verify native image ownership'
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    (root/'private/var').mkdir(parents=True)
    (root/'tmp').symlink_to('private/tmp')
    apply_var(root)
    prefs = root/'private/var/mobile/Library/Preferences'
    migration = plistlib.loads((prefs/'com.apple.migration.plist').read_bytes())
    assert migration['LastSystemVersion'] == '20F66'
    assert migration['DMLastMigrationResults']['success'] is True
    assert migration['DMUserDataDisposition'] == {
        'SyntheticDidUpgrade': False, 'buildVersion': '20F66'}
    assert plistlib.loads((prefs/'com.apple.springboard.plist').read_bytes())['BKNoWatchdogs'] is True
    assert plistlib.loads((prefs/'com.apple.purplebuddy.plist').read_bytes())['SetupFinishedAllSteps'] is True
    originals = {p.name:p.read_bytes() for p in prefs.glob('*.plist')}
    stage(root)
    seed = root/SEED.lstrip('/')
    found = set()
    for line in (seed/'manifest.tsv').read_text().splitlines():
        fields = line.split('\t')
        if fields[0] != 'f' or not fields[4].startswith('/private/var/mobile/Library/Preferences/'):
            continue
        assert fields[1:4] == ['501', '501', '600']
        name = Path(fields[4]).name
        assert (seed/'files'/fields[5]).read_bytes() == originals[name]
        found.add(name)
    assert found == set(originals)
    print('PASS: all', len(found), 'preference domains retained in native RAMFS template with mobile ownership')
