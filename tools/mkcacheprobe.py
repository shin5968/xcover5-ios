#!/usr/bin/env python3
"""Own iOS-platform LC_MAIN probe. Original Apple dyld is injected only locally."""
from pathlib import Path
import sys
import mkdynamic
from mkappleprobe import LOADER
if __name__ == '__main__':
    obj, out = map(Path, sys.argv[1:])
    out.write_bytes(mkdynamic.build(obj.read_bytes(), 'app', LOADER, platform=2, apple_metadata=True))
