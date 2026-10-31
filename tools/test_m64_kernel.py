"""Check the M64 boot-view contract and execute the actual C parser/strategy.

Synthetic 16/24MiB fixtures contain no original iOS files and are not flashable.
The same test_m20_view.py also accepts final local Odin boot images.
"""
from pathlib import Path
import argparse
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = b'XCOVER5 M64 BOOT_HFS'


def fixture(size):
    payload = bytearray(1024 + size)
    payload[:8] = b'SWEETXNU'
    struct.pack_into('<II', payload, 8, 1, 2)
    struct.pack_into('<4Q', payload, 0x2a8 + 32,
                     0xfffffe00081c0000, size, 1024, size)
    payload[2048:2052] = b'HX\0\5'
    struct.pack_into('>II', payload, 2048 + 40, 4096, size // 4096)
    boot = bytearray(4096)
    boot[:8] = b'ANDROID!'
    struct.pack_into('<I', boot, 8, 16)
    struct.pack_into('<I', boot, 16, len(payload))
    struct.pack_into('<II', boot, 36, 2048, 2)
    return boot + payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('kernels', type=Path, nargs='?')
    args = parser.parse_args()
    if args.source.is_dir():
        source = (args.source / 'bsd/dev/xchfs.h').read_text()
        for text in ('vs!=16*1024*1024 && vs!=24*1024*1024',
                     'xc_le64(b+8)<vs', 'vo<table_end', 'vs>rd-vo',
                     '(uint64_t)bs*bc!=vs', MARKER.decode()):
            assert text in source, 'applied M64 contract missing: ' + text
    else:
        assert args.kernels is not None, 'applied source missing'
    if args.kernels is not None:
        kernels = [p for p in args.kernels.glob('kernel.*') if p.is_file()]
        assert kernels and all(MARKER in p.read_bytes() for p in kernels), 'M64 kernel missing'
    with tempfile.TemporaryDirectory() as temporary:
        for mib in (16, 24):
            boot = Path(temporary) / f'parser-fixture-{mib}.img'
            boot.write_bytes(fixture(mib * 1024**2))
            subprocess.run([sys.executable, str(ROOT / 'tools/test_m20_view.py'),
                            str(ROOT / 'xnu/patches/0036-xcover5-hfs-emmc-view.patch'),
                            str(boot)], check=True)
    print('M64 exact 16/24MiB C parser, bounds, header geometry and read-only strategy PASS')


if __name__ == '__main__':
    main()
