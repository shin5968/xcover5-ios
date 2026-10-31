"""Merge local IPSW UI identity while preserving the Samsung hardware tree.

Only metadata is copied. No Apple MMIO, CPU, interrupt, memory, MAC, ECID,
serial, camera or haptic nodes are admitted. The original tree stays local.
"""
from pathlib import Path
import copy,hashlib,json,struct,sys
import adt

PRODUCT_KEYS=frozenset(('product-id','product-name','product-description',
 'artwork-device-idiom','artwork-device-subtype','artwork-scale-factor',
 'artwork-dynamic-displaymode','artwork-display-gamut','compatible-app-variant',
 'compatible-device-fallback','device-color-policy','mobiledevice-min-ver',
 'mobiledevice-beta-min-ver','activation-protocol-version','udid-version',
 'allow-32bit-apps','ui-reachability','thin-bezel'))

def parse(data):
    tree,end=adt.parse(data)
    if end!=len(data) or adt.serialize(tree)!=data:
        raise ValueError('noncanonical/incomplete ADT')
    return tree

def setprop(node,key,value):
    node.props=[(k,f,v) for k,f,v in node.props if k!=key]+[(key,0,value)]

def merge(samsung,original):
    base=parse(samsung);source=parse(original);out=copy.deepcopy(base)
    model=source.prop('model')
    if model!=b'iPhone10,3\0' or source.prop('target-type')!=b'D22\0':
        raise ValueError('requires verified iOS16.5 D22AP profile')
    product=next((c for c in source.children if c.name=='product'),None)
    if product is None or len(product.prop('product-id') or b'')!=20:
        raise ValueError('missing model product-id')
    if any(c.name=='product' for c in out.children):
        raise ValueError('existing product node requires explicit reconciliation')
    new=adt.Node();new.props=[('name',0,b'product\0')]
    for k,f,v in product.props:
        if k in PRODUCT_KEYS and not f and v and b'syscfg/' not in v:
            new.props.append((k,0,v))
    # Matches the verified native framebuffer profile. No GPU capability is claimed.
    setprop(new,'artwork-scale-factor',struct.pack('<I',2))
    setprop(new,'artwork-display-gamut',b'sRGB\0')
    out.children.append(new)
    setprop(out,'model',model);setprop(out,'target-type',source.prop('target-type'))
    # Keep all preexisting matching tokens in the same order, including xiaomi,sweet.
    tokens=(out.prop('compatible') or b'').rstrip(b'\0').split(b'\0')
    for token in (b'D22AP',b'iPhone10,3'):
        if token not in tokens:tokens.append(token)
    setprop(out,'compatible',b'\0'.join(tokens)+b'\0')
    chosen=next(c for c in out.children if c.name=='chosen')
    setprop(chosen,'display-scale',struct.pack('<I',2))
    # Every other byte of the hardware tree must remain identical.
    check=copy.deepcopy(out);check.children=[c for c in check.children if c.name!='product']
    for key in ('model','target-type','compatible'):
        check.props=[p for p in check.props if p[0]!=key]
    ref=copy.deepcopy(base);ref.props=[p for p in ref.props if p[0] not in ('model','target-type','compatible')]
    for tree in (check,ref):
        c=next(c for c in tree.children if c.name=='chosen')
        c.props=[p for p in c.props if p[0]!='display-scale']
    if adt.serialize(check)!=adt.serialize(ref):raise ValueError('hardware tree changed')
    result=adt.serialize(out);parse(result)
    return result,dict(base_sha256=hashlib.sha256(samsung).hexdigest(),
      original_sha256=hashlib.sha256(original).hexdigest(),result_sha256=hashlib.sha256(result).hexdigest(),
      product_keys=[k for k,f,v in new.props],hardware_tree='byte-identical excluding explicit UI identity/scale allowlist',
      physical_drivers='unchanged; Apple hardware nodes excluded')

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: port_hackios_identity.py SAMSUNG.adt ORIGINAL_D22AP.adt OUT.adt')
    output=Path(sys.argv[3])
    if output.exists():raise SystemExit('refusing to overwrite '+str(output))
    data,report=merge(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).read_bytes())
    output.write_bytes(data);output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
