#!/usr/bin/env python3
"""M31 explicit malloc/pthread imports using the verified M30 layout."""
from pathlib import Path
import sys
import mkinit
import mklibsystemprobe
IMPORTS=(b'_malloc',b'_free',b'_pthread_create',b'_pthread_join',b'_pthread_self')
def build_code(code,start=0):
    return mklibsystemprobe.build_code(code,start,imports=IMPORTS)
if __name__=='__main__':
    Path(sys.argv[2]).write_bytes(build_code(*mkinit.text_of(Path(sys.argv[1]).read_bytes())))
