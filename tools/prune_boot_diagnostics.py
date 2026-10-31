"""Remove only completed owned regression probes from a staged image."""
from pathlib import Path
import json, plistlib, sys
from stage_m63_resources import safe_path

JOBS = {'org.xcover5.m35.proof','org.xcover5.m36.echo','org.xcover5.m37.echo','org.xcover5.m38.notify'}
PROGRAMS = {f'/sbin/m{n}-probe' for n in range(21,39) if n != 34}
PROGRAMS |= {'/sbin/m22-loader','/sbin/m23-code','/sbin/m35-proof','/sbin/m37-server','/sbin/m37-client'}
PROGRAMS |= {'/usr/lib/libm25.dylib','/usr/lib/libm26.dylib'}

def prune(root):
    root=Path(root).resolve(strict=True)
    assert safe_path(root,'/sbin/launchd').is_file(), 'expected staged boot root'
    jobs=root/'System/Library/LaunchDaemons'
    deletions=[]
    for label in JOBS:
        path=safe_path(root,'/System/Library/LaunchDaemons/'+label+'.plist')
        if path.exists():
            job=plistlib.loads(path.read_bytes())
            assert job.get('Label')==label and not path.is_symlink()
            deletions.append(path)
    for path in jobs.glob('*.plist'):
        if path in deletions:continue
        job=plistlib.loads(path.read_bytes())
        def strings(value):
            if isinstance(value,str):return [value]
            if isinstance(value,dict):return [s for v in value.values() for s in strings(v)]
            if isinstance(value,list):return [s for v in value for s in strings(v)]
            return []
        referenced=strings(job.get('Program',''))+strings(job.get('ProgramArguments',[]))
        if set(referenced)&PROGRAMS:
            raise ValueError('retained job uses a proposed removal: '+path.name)
    for name in sorted(PROGRAMS):
        path=safe_path(root,name)
        if path.exists():
            if not path.is_file() or path.is_symlink():raise ValueError('unexpected probe type: '+name)
            deletions.append(path)
    # Validate the complete allowlisted write set before any removal; never recurse.
    report=[dict(path='/'+p.relative_to(root).as_posix(),bytes=p.stat().st_size) for p in deletions]
    for path in deletions:path.unlink()
    print(json.dumps(dict(removed=report,bytes=sum(p['bytes'] for p in report)),indent=2))
    return report

if __name__=='__main__':prune(Path(sys.argv[1]))
