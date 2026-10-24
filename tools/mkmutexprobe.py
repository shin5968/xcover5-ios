#!/usr/bin/env python3
"""M32 standard libSystem bindings for a mutex-protected two-worker test."""
from pathlib import Path
import sys
import mkinit
import mklibsystemprobe
IMPORTS=(b'_pthread_mutex_init',b'_pthread_mutex_lock',b'_pthread_mutex_unlock',b'_pthread_mutex_destroy',b'_pthread_create',b'_pthread_join')
def build_code(code,start=0):
    return mklibsystemprobe.build_code(code,start,imports=IMPORTS)
if __name__=='__main__':
    Path(sys.argv[2]).write_bytes(build_code(*mkinit.text_of(Path(sys.argv[1]).read_bytes())))
