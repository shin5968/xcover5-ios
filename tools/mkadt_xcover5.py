#!/usr/bin/env python3
"""Single-core XCover5 early-boot ADT. Not an iOS userland device tree."""
import sys
import adt
import sweet_adt_base as base
# A contiguous low-bank interval with no reservations in collected live iomem.
# Loader must still check its payload/shim/DTB do not overlap this interval.
base.PHYS_BASE = 0xa0000000
base.MEM_SIZE = 0x10000000
base.QEMU_TIMEBASE = 26000000
base.FB, base.FB_SIZE = 0xfa000000, 0x1400000
base.FB_W, base.FB_H, base.FB_STRIDE = 720, 1480, 2880

def setprop(n, key, value):
    n.props = [(k, f, value if k == key else v) for k, f, v in n.props]

def build():
    root = base.build(qemu=True)
    byname = {dict((k,v) for k,f,v in n.props)['name'].rstrip(b'\0'):n for n in root.children}
    # Early kernel has no corecrypto provider yet. These optional identity
    # fields trigger generatePlatformUUID -> SHA1Init(NULL provider).
    chosen = byname[b'chosen']
    chosen.props = [(k,f,v) for k,f,v in chosen.props
                    if k not in ('unique-chip-id', 'chip-id')]
    cpu = byname[b'cpus'].children[0]
    setprop(cpu, 'compatible', base.cstr('arm,cortex-a55') + base.cstr('qcom,kryo470') + base.cstr('ARM,v8'))
    setprop(cpu, 'clock-frequency', base.u32(2000000000))
    gic = byname[b'arm-io'].children[0]
    setprop(gic, 'compatible', base.cstr('arm,gic-400'))
    setprop(gic, 'reg', base.u64(0x12a01000-base.SOC_BASE,0x1000,0x12a02000-base.SOC_BASE,0x1000))
    # Keep xiaomi,sweet only to match the reused early platform expert.
    setprop(root, 'compatible', base.cstr('samsung,xcover5') + base.cstr('xiaomi,sweet') + base.cstr('AppleARM'))
    return root

if __name__ == '__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: mkadt_xcover5.py OUT.adt')
    blob = adt.serialize(build())
    with open(sys.argv[1], 'wb') as f: f.write(blob)
    print(f'{sys.argv[1]}: {len(blob)} bytes; 1 CPU, 26MHz, GICv2, 255MiB usable RAM')
