"""Owned fixtures only: prove the identity allowlist preserves hardware mappings."""
import struct
import adt
from port_hackios_identity import merge,parse

def node(name,props=(),children=()):
    n=adt.Node();n.props=[('name',0,name.encode()+b'\0')]+list(props);n.children=list(children);return n
base=node('device-tree',[('model',0,b'iPhone10,3\0'),('compatible',0,b'samsung,xcover5\0xiaomi,sweet\0AppleARM\0')],
 [node('chosen',[('dram-base',0,struct.pack('<Q',0xa0000000)),('dram-size',0,struct.pack('<Q',0xff00000)),('display-scale',0,struct.pack('<I',3))]),
 node('arm-io',[('ranges',0,b'owned Samsung MMIO')]),node('cpus',[('reg',0,b'owned cpu affinity')])])
orig=node('device-tree',[('model',0,b'iPhone10,3\0'),('target-type',0,b'D22\0'),('unique-chip-id',0,b'NEVER-COPY')],
 [node('product',[('product-id',0,b'owned test model id!'),('product-name',0,b'owned UI profile\0'),('wifi-chipset',0,b'NEVER-COPY'),('device-colors',1,b'syscfg/NEVER-COPY')],
 [node('camera',[('reg',0,b'NEVER-COPY')])]),node('arm-io',[('ranges',0,b'NEVER-COPY')])])
raw=adt.serialize(base);original=adt.serialize(orig)
out,report=merge(raw,original);assert b'NEVER-COPY' not in out
root=parse(out);assert root.prop('compatible').startswith(base.prop('compatible'))
assert root.children[1].props==base.children[1].props and root.children[2].props==base.children[2].props
assert len(root.children)==4 and root.children[3].name=='product' and not root.children[3].children
assert root.children[0].prop('dram-size')==struct.pack('<Q',0xff00000)
assert root.children[0].prop('display-scale')==struct.pack('<I',2)
for a,b in [(raw,original+b'bad'),(out,original),(raw,raw)]:
    try:merge(a,b)
    except ValueError:pass
    else:raise AssertionError('invalid/duplicate identity admitted')
assert adt.serialize(base)==raw and adt.serialize(orig)==original
print('M72 identity: original source immutable, Samsung RAM/CPU/MMIO retained, hardware/placeholder exclusion, scale2, malformed/wrong/duplicate profiles rejected PASS')
