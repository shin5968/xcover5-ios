"""M63 original lifecycle resources and the HackiOS writable-data recipe."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import plistlib
import sys

CONFIG = Path(__file__).resolve().parents[1] / 'third_party/hackios-ui-bringup/m63'
FILES = json.loads((CONFIG / 'FILES.json').read_text())
MARKERS = (
    '/private/var/db/diagnostics/.migrated',
    '/private/var/db/diagnostics/timesync/.migrated',
    '/private/var/db/uuidtext/.migrated',
)
UI_LOGS = {'com.apple.backboardd', 'com.apple.SpringBoard'}


def placeholder(name):
    return hashlib.shake_256(('XCOVER5 M63 LOCAL RESOURCE ' + name).encode()).digest(FILES[name][0])


def inject(image, source):
    for name, (size, digest) in FILES.items():
        data = (source / name).read_bytes()
        assert len(data) == size and hashlib.sha256(data).hexdigest() == digest, name
        stub = placeholder(name)
        assert image.count(stub) == 1, name
        image = image.replace(stub, data, 1)
    return image


def metadata():
    records = {}
    for line in (CONFIG / 'var.skel').read_text().splitlines():
        fields = line.split('\t')
        if fields[0] == 'd':
            kind, mode, uid, gid, name = fields
            item = dict(kind=kind, mode=int(mode, 8), uid=int(uid), gid=int(gid))
        else:
            kind, target, name = fields
            assert kind == 'l' and target.startswith('/')
            item = dict(kind=kind, target=target, uid=0, gid=0)
        path = PurePosixPath(name)
        assert str(path) == name and '..' not in path.parts
        assert name.startswith('/private/var/') and name not in records
        records[name] = item
    for source in sorted((CONFIG / 'seed-preferences').glob('*.plist')):
        name = '/private/var/mobile/Library/Preferences/' + source.name
        records[name] = dict(kind='f', mode=0o644, uid=501, gid=501, source=source)
    for name in MARKERS:
        records[name] = dict(kind='f', mode=0o644, uid=272, gid=272, data=b'')
    return records


def safe_path(root, name):
    path = PurePosixPath(name)
    assert path.is_absolute() and '..' not in path.parts
    result = root
    for component in path.parts[1:]:
        result = result / component
        # Never follow an existing image symlink while creating directories/files.
        if result.is_symlink():
            raise ValueError('symlink in image write path: ' + str(result))
    return result


def set_owner(path, uid, gid, link=False):
    if link:
        os.lchown(path, uid, gid)
    else:
        os.chown(path, uid, gid)


def stage(root):
    for name in FILES:
        path = safe_path(root, '/' + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(placeholder(name))
        path.chmod(0o644)
    # Match upstream's focused console logging instead of enabling DT mode for
    # every support daemon. This is a verbosity choice, not a storage quota.
    from stage_hackios_boot import LABELS
    for label in LABELS:
        path = root / 'System/Library/LaunchDaemons' / (label + '.plist')
        job = plistlib.loads(path.read_bytes())
        if label not in UI_LOGS:
            job.get('EnvironmentVariables', {}).pop('OS_ACTIVITY_DT_MODE', None)
        path.write_bytes(plistlib.dumps(job, fmt=plistlib.FMT_BINARY))
        path.chmod(0o644)
    print('M63 staged', len(FILES), 'pinned original resources; UI console logging focused')


def apply_var(root, owner=set_owner):
    records = metadata()
    for name, item in records.items():
        if item['kind'] != 'd':
            continue
        path = safe_path(root, name)
        path.mkdir(parents=True, exist_ok=True)
    for name, item in records.items():
        if item['kind'] != 'f':
            continue
        path = safe_path(root, name)
        path.write_bytes(item['source'].read_bytes() if 'source' in item else item['data'])
    # Links are last: no earlier write can traverse a just-created link.
    for name, item in records.items():
        if item['kind'] != 'l':
            continue
        parent = safe_path(root, str(PurePosixPath(name).parent))
        path = parent / PurePosixPath(name).name
        if os.path.lexists(path):
            assert path.is_symlink() and os.readlink(path) == item['target'], name
        else:
            path.symlink_to(item['target'])
        owner(path, item['uid'], item['gid'], True)
    # This runs AFTER mkhfsroot's blanket ownership pass. Preserve mixed native
    # owners, including logd272, analyticsd263, installd33 and mobile501.
    for name, item in records.items():
        if item['kind'] == 'l':
            continue
        path = safe_path(root, name)
        path.chmod(item['mode'])
        owner(path, item['uid'], item['gid'], False)
    print('M63 applied native var metadata:', len(records), 'entries; fresh-log markers restored')


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve(strict=True)
    assert (root / 'sbin/launchd').is_file(), 'expected mounted build image'
    if len(sys.argv) > 2 and sys.argv[2] == '--apply-var':
        apply_var(root)
    else:
        stage(root)
