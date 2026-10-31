"""M67 restores one hash-pinned original BackBoard config only after local injection."""
from pathlib import Path
import hashlib
import sys
from stage_m63_resources import safe_path

NAME = 'System/Library/BackBoard/EventProcessorConfiguration.plist'
SIZE = 1313
SHA256 = '1360a59a33789cebea9db2f652ddaf42c6978158a98c2fce72cb43810ea9ed01'

def placeholder():
    return hashlib.shake_256(('XCOVER5 M67 LOCAL RESOURCE ' + NAME).encode()).digest(SIZE)

def stage(root):
    path = safe_path(root, '/' + NAME)
    if path.exists() or path.is_symlink():
        raise ValueError('M67 config path already exists')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o755)
    path.write_bytes(placeholder())
    path.chmod(0o644)

def inject(image, source):
    data = (source / NAME).read_bytes()
    assert len(data) == SIZE and hashlib.sha256(data).hexdigest() == SHA256
    stub = placeholder()
    assert image.count(stub) == 1, 'M67 placeholder missing, duplicated or fragmented'
    return image.replace(stub, data, 1)

if __name__ == '__main__':
    stage(Path(sys.argv[1]))
