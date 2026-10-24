#!/usr/bin/env python3
"""Public metadata + compressible synthetic placeholders; no Apple bytes."""
import hashlib
import json
import sys
from pathlib import Path

LAYOUT = Path(__file__).with_name('cache-layout.json')

def token(name):
    return b'XCOVER5-M28-PLACEHOLDER\0' + hashlib.sha256(name.encode()).digest()

def block(name):
    t = token(name)
    return t + bytes(4096-len(t))

def create(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for item in json.loads(LAYOUT.read_text()):
        assert item['size'] % 4096 == 0
        chunk = block(item['file']) * 256
        with (directory / item['file']).open('xb') as f:
            remaining = item['size']
            while remaining:
                part = chunk[:min(remaining, len(chunk))]
                f.write(part)
                remaining -= len(part)

def assembly():
    lines = ['.p2align 3', 'cache_records:']
    items = json.loads(LAYOUT.read_text())
    for item in items:
        lines += [f" .quad {item['size']}",
                  f" .word {item['head_crc']}, {item['tail_crc']}",
                  f" .asciz \"/System/Library/Caches/com.apple.dyld/{item['file']}\"", '.p2align 3']
    lines += ['cache_records_end:']
    return '\n'.join(lines)+'\n'

if __name__ == '__main__':
    if sys.argv[1] == 'assembly':
        Path(sys.argv[2]).write_bytes(assembly().encode())
    else:
        create(Path(sys.argv[1]))
