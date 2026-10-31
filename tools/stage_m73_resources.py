"""Stage only the current CoreDuet model; original Apple bytes remain local."""
from pathlib import Path, PurePosixPath
import hashlib, json, os, sys
from stage_m63_resources import safe_path

CONFIG = Path(__file__).resolve().parents[1] / 'third_party/hackios-ui-bringup/m73'
FILES = json.loads((CONFIG / 'FILES.json').read_text())
DIRECTORY = 'System/Library/PrivateFrameworks/CoreDuet.framework/_DKDataModel.momd'
EXPECTED = {DIRECTORY + '/' + n for n in ('VersionInfo.plist', '_DKDataModel35.mom', '_DKDataModel35.omo')}
if set(FILES) != EXPECTED:
    raise ValueError('M73 accepts only the three current CoreDuet model files')
for name, (size, digest) in FILES.items():
    if not isinstance(size, int) or not 0 < size <= 128 * 1024 or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid M73 resource metadata: ' + name)

def placeholder(name):
    return hashlib.shake_256(('XCOVER5 M73 LOCAL COREDUET MODEL ' + name).encode()).digest(FILES[name][0])

def stage(root):
    root = Path(root)
    parent = safe_path(root, '/' + str(PurePosixPath(DIRECTORY).parent))
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError('M73 requires the existing physical CoreDuet framework namespace')
    folder = safe_path(root, '/' + DIRECTORY)
    if folder.exists() or folder.is_symlink():
        raise ValueError('M73 refuses to replace an existing model')
    for name in FILES:
        safe_path(root, '/' + name)
    folder.mkdir(); folder.chmod(0o755); os.chown(folder, 0, 0)
    for name in FILES:
        path = safe_path(root, '/' + name)
        path.write_bytes(placeholder(name)); path.chmod(0o644); os.chown(path, 0, 0)
    print('M73 current CoreDuet model placeholders', len(FILES), 'bytes', sum(v[0] for v in FILES.values()))

def inject(image, source):
    replacements = []
    for name, (size, digest) in FILES.items():
        data = (Path(source) / name).read_bytes()
        assert len(data) == size and hashlib.sha256(data).hexdigest() == digest, name
        stub = placeholder(name)
        assert image.count(stub) == 1, 'missing/duplicate/fragmented M73 placeholder: ' + name
        replacements.append((stub, data))
    for stub, data in replacements:
        image = image.replace(stub, data, 1)
    return image

if __name__ == '__main__':
    stage(Path(sys.argv[1]))
