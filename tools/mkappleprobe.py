#!/usr/bin/env python3
"""Build our M27 app and a NON-EXECUTABLE placeholder, never Apple code.

The placeholder must be replaced locally before packaging. It deliberately
has no Mach-O header so accidentally flashing CI output fails closed at exec.
"""
import hashlib
import sys
from pathlib import Path
import mkdynamic

DYLD_SIZE = 922912
DYLD_SHA256 = 'a453aa234fc9bd440dc4e55bd2e18f9a7eb2bc3fd7ef319d8714a664bc55bf5c'
LOADER = b'/emmc/usr/lib/m27-apple-dyld\0'


def placeholder():
    return hashlib.shake_256(b'XCOVER5 M27 LOCAL APPLE DYLD PLACEHOLDER v1').digest(DYLD_SIZE)


if __name__ == '__main__':
    obj, app, stub = map(Path, sys.argv[1:])
    app.write_bytes(mkdynamic.build(obj.read_bytes(), 'app', LOADER))
    stub.write_bytes(placeholder())
