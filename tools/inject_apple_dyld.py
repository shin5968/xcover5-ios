#!/usr/bin/env python3
"""Local-only equal-length replacement of a unique contiguous HFS placeholder.

Fail closed if fragmented or already replaced. Never changes the input image,
the Apple binary, catalog, extents, or file length. Extract the output with an
independent HFS reader and verify its dyld before packaging it for a device.
"""
import hashlib
import sys
from pathlib import Path
from mkappleprobe import placeholder, DYLD_SIZE, DYLD_SHA256


def inject(image, dyld):
    if len(dyld) != DYLD_SIZE or hashlib.sha256(dyld).hexdigest() != DYLD_SHA256:
        raise ValueError('Apple dyld provenance/hash mismatch')
    if image[1024:1026] not in (b'H+', b'HX'):
        raise ValueError('Not a raw HFS image')
    stub = placeholder()
    if image.count(stub) != 1:
        raise ValueError('Placeholder missing, fragmented or duplicated; refusing replacement')
    off = image.index(stub)
    if off < 1536:
        raise ValueError('Invalid data extent')
    return image[:off] + dyld + image[off+len(stub):], off


if __name__ == '__main__':
    src, loader, dst = map(Path, sys.argv[1:])
    if dst.exists() or dst.resolve() in (src.resolve(), loader.resolve()):
        raise ValueError('Output must be a new file')
    output, offset = inject(src.read_bytes(), loader.read_bytes())
    dst.write_bytes(output)
    print('Local dyld injected at', hex(offset), 'output SHA256', hashlib.sha256(output).hexdigest())
