"""Exercise the actual M63 resource injector, metadata recipe and path guards."""
from pathlib import Path
import hashlib
import os
import plistlib
import stat
import tempfile
import stage_hackios_boot as graph
import stage_m63_resources as m63

records = m63.metadata()
assert sum(x['kind'] == 'd' for x in records.values()) == 111
assert sum(x['kind'] == 'l' for x in records.values()) == 2
for name, expected in {
    '/private/var/installd': (33, 33, 0o755),
    '/private/var/db/analyticsd': (263, 263, 0o750),
    '/private/var/db/diagnostics': (272, 272, 0o751),
    '/private/var/mobile': (501, 501, 0o711),
    '/private/var/run': (0, 1, 0o775),
}.items():
    item = records[name]
    assert (item['uid'], item['gid'], item['mode']) == expected
assert len(m63.FILES) == 79
assert 'System/Library/LifecyclePolicy/DomainAttributes/com.apple.frontboard.plist' in m63.FILES
assert records['/private/var/db/timezone/zoneinfo']['target'] == '/usr/share/zoneinfo.default'
assert records['/private/var/db/timezone/localtime']['target'].endswith('/zoneinfo/UTC')
assert 'usr/share/zoneinfo.default/UTC' in m63.FILES

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / 'root'
    (root / 'System/Library/LaunchDaemons').mkdir(parents=True)
    (root / 'private/etc').mkdir(parents=True)
    graph.stage(root)
    m63.stage(root)
    for label in graph.LABELS:
        original = plistlib.loads((graph.CONFIG / 'jobs' / (label + '.plist')).read_bytes())
        expected = graph.job(original)
        if label not in m63.UI_LOGS:
            expected['EnvironmentVariables'].pop('OS_ACTIVITY_DT_MODE', None)
        actual = plistlib.loads((root / 'System/Library/LaunchDaemons' / (label + '.plist')).read_bytes())
        assert actual == expected, label
    ownership = {}

    def owner(path, uid, gid, link=False):
        ownership['/' + path.relative_to(root).as_posix()] = (uid, gid, link)

    m63.apply_var(root, owner)
    m63.apply_var(root, owner)  # Reapplying the fresh image recipe is idempotent.
    for name, item in records.items():
        path = root / name.lstrip('/')
        assert ownership[name] == (item['uid'], item['gid'], item['kind'] == 'l')
        if item['kind'] == 'l':
            assert path.is_symlink() and os.readlink(path) == item['target']
        else:
            assert stat.S_IMODE(path.stat().st_mode) == item['mode']
        if item['kind'] == 'f':
            assert path.read_bytes() == (item['source'].read_bytes() if 'source' in item else b'')
    assert all((root / name.lstrip('/')).stat().st_size == 0 for name in m63.MARKERS)
    outside = Path(temporary) / 'outside'
    outside.mkdir()
    (root / 'escape').symlink_to(outside, target_is_directory=True)
    for name in ('/escape/new', '/private/var/../../escape/new'):
        try:
            m63.safe_path(root, name)
        except (ValueError, AssertionError):
            pass
        else:
            raise AssertionError('unsafe image write path accepted')
    assert list(outside.iterdir()) == []
    old = m63.FILES
    try:
        data = b'owned-m63-resource'
        m63.FILES = {'owned': (len(data), hashlib.sha256(data).hexdigest())}
        (root / 'owned').write_bytes(data)
        stub = m63.placeholder('owned')
        assert m63.inject(b'A' + stub + b'Z', root) == b'A' + data + b'Z'
        for image, source in ((b'missing', data), (stub + stub, data), (stub, b'bad')):
            (root / 'owned').write_bytes(source)
            try:
                m63.inject(image, root)
            except AssertionError:
                pass
            else:
                raise AssertionError('invalid resource/placeholder accepted')
    finally:
        m63.FILES = old

print('M63 actual 111 directories/2 links/8 seed prefs/3 markers, mixed owners, logging profile, path safety and injection rejection PASS')
