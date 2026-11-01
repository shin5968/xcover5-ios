"""Hash-only profile service cache and demand job for the development port."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,plistlib,sys
from stage_m63_resources import safe_path
from stage_m66_icu import CACHE
from stage_m74_var import SEED
CONFIG=Path(__file__).resolve().parents[1]/'third_party/hackios-ui-bringup/m79'
FILES=json.loads((CONFIG/'FILES.json').read_text())
PROGRAM='usr/libexec/profiled'
JOB='System/Library/LaunchDaemons/com.apple.managedconfiguration.profiled.plist'
PREFIX='xcover-m79'
ASSETS={n:v for n,v in FILES.items() if n!=JOB}
def block(name):
    token=b'XCOVER5-M79-PROFILED\0'+hashlib.sha256(name.encode()).digest()
    return token+bytes(4096-len(token))
def job():
    # Pinned HackiOS --rest policy removes KeepAlive and LaunchEvents from
    # the source job. Original service names, mobile identity and spawn type.
    return dict(Label='com.apple.managedconfiguration.profiled',
        ProgramArguments=['/usr/libexec/profiled'], UserName='mobile',
        POSIXSpawnType='Adaptive', EnablePressuredExit=True,EnableTransactions=True,
        ThrottleInterval=0, MachServices={n:True for n in (
            'com.apple.managedconfiguration.profiled','com.apple.managedconfiguration.profiled.public')},
        StandardErrorPath='/dev/console',
        EnvironmentVariables={'OS_ACTIVITY_DT_MODE':'YES'})
def cache(root):
    root=Path(root); target=safe_path(root,'/'+PREFIX)
    assert not target.exists()
    for name,(size,_) in ASSETS.items():
        p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
        path=safe_path(root,'/'+PREFIX+'/'+name);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:
            pattern=block(name)*256
            for at in range(0,size,len(pattern)):f.write(pattern[:min(len(pattern),size-at)])
        path.chmod(0o555 if name==PROGRAM else 0o444);os.chown(path,0,0)
    for directory,dirs,files in os.walk(target,topdown=False):
        p=Path(directory);p.chmod(0o555);os.chown(p,0,0)
    print('M79 cache assets',len(ASSETS))
def stage_root(root):
    root=Path(root)
    for name in list(ASSETS)+[JOB]:
        p=safe_path(root,'/'+name);assert not p.exists() and not p.is_symlink(),name
    for name in ASSETS:
        p=safe_path(root,'/'+name);p.parent.mkdir(parents=True,exist_ok=True)
        p.symlink_to(CACHE+PREFIX+'/'+name);os.lchown(p,0,0)
    p=safe_path(root,'/'+JOB);p.write_bytes(plistlib.dumps(job(),fmt=plistlib.FMT_BINARY));p.chmod(0o644);os.chown(p,0,0)
    # Native RAMFS needs the mobile service's data directories on every boot.
    manifest=safe_path(root,SEED+'/manifest.tsv')
    rows=[line.split('\t') for line in manifest.read_text().splitlines()]
    known={r[4]:r for r in rows}
    for tail in ('ConfigurationProfiles','UserConfigurationProfiles'):
        name='/private/var/mobile/Library/'+tail
        if name in known:assert known[name][:4]==['d','501','501','700']
        else:rows.append(['d','501','501','700',name])
    assert len(rows)<=512
    manifest.write_bytes(''.join('\t'.join(r)+'\n' for r in rows).encode())
    print('M79 demand job, cache links',len(ASSETS),'RAMFS records',len(rows))
if __name__=='__main__':{'cache':cache,'root':stage_root}[sys.argv[1]](Path(sys.argv[2]))
