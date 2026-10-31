"""M66 ICU paths and synthetic cache-volume placeholders; no original bytes."""
from pathlib import Path
import hashlib
import sys
from stage_m63_resources import safe_path

FILES = {
    'icudt70l.dat': (30447056, 'd2d5f82e30f4c193d48da78604381fa551adab548e2533e1ae6139538336f736'),
    'icutzformat.txt': (3, '327d09f9e798492441b2a7839e2ce11498c64ae4c36ea98e248b89c5fc3172fe'),
}
CACHE = '/System/Library/Caches/com.apple.dyld/'

def block(name):
    token = b'XCOVER5-M66-ICU-PLACEHOLDER\0' + hashlib.sha256(name.encode()).digest()
    return token + bytes(4096 - len(token))

def stage_root(root):
    directory = safe_path(root, '/usr/share/icu')
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o755)
    for name in FILES:
        path = directory / name
        if path.exists() or path.is_symlink():
            raise ValueError('refuse to replace existing ICU path: ' + str(path))
        path.symlink_to(CACHE + name)

def stage_cache(root):
    for name, (size, _) in FILES.items():
        data = block(name)
        with (root / name).open('xb') as file:
            for start in range(0, size, len(data)):
                file.write(data[:min(len(data), size - start)])
        (root / name).chmod(0o444)

if __name__ == '__main__':
    {'root': stage_root, 'cache': stage_cache}[sys.argv[1]](Path(sys.argv[2]))
