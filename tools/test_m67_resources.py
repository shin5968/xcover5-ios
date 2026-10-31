"""Test actual M67 staging and original-byte substitution guards with owned data."""
from pathlib import Path
import hashlib
import stat
import tempfile
import stage_m67_resources as resource

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    resource.stage(root)
    target = root / resource.NAME
    assert target.read_bytes() == resource.placeholder()
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o755
    try:
        resource.stage(root)
    except ValueError:
        pass
    else:
        raise AssertionError('existing resource was overwritten')
    old_size,old_hash=resource.SIZE,resource.SHA256
    try:
        owned=b'owned event configuration test'
        resource.SIZE=len(owned)
        resource.SHA256=hashlib.sha256(owned).hexdigest()
        stub=resource.placeholder();target.write_bytes(owned)
        assert resource.inject(b'A'+stub+b'Z',root)==b'A'+owned+b'Z'
        for image,data in ((b'missing',owned),(stub+stub,owned),(stub,b'corrupt')):
            target.write_bytes(data)
            try:
                resource.inject(image,root)
            except AssertionError:
                pass
            else:
                raise AssertionError('invalid resource substitution accepted')
    finally:
        resource.SIZE,resource.SHA256=old_size,old_hash
print('M67 actual staging modes, overwrite rejection and wrong-source/missing/duplicate placeholder guards PASS')
