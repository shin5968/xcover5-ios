"""Save the reviewed fresh var template outside its future RAMFS mount."""
from pathlib import Path, PurePosixPath
import os, stat, sys
from stage_m63_resources import safe_path
SEED = '/usr/share/xcover5/m74-var-template'

def stage(root):
    root = Path(root)
    var = safe_path(root, '/private/var')
    seed = safe_path(root, SEED)
    if not var.is_dir() or seed.exists():
        raise ValueError('expected unmodified M73 var and a new seed directory')
    rows = []
    for directory, dirs, files in os.walk(var, followlinks=False):
        for path in [Path(directory)] + [Path(directory)/n for n in dirs+files if (Path(directory)/n).is_symlink() or not (Path(directory)/n).is_dir()]:
            st = path.lstat(); kind = stat.S_IFMT(st.st_mode)
            if kind not in (stat.S_IFDIR, stat.S_IFREG, stat.S_IFLNK):
                raise ValueError('unexpected var seed object: '+str(path))
            name = '/' + path.relative_to(root).as_posix()
            assert name == '/private/var' or name.startswith('/private/var/')
            assert not any(c in name for c in '\t\r\n')
            rows.append((name, st, path))
    rows.sort(key=lambda row:(len(PurePosixPath(row[0]).parts), row[0]))
    assert rows[0][0] == '/private/var' and len(rows) <= 512
    # All template storage is root-owned; native destination metadata lives in
    # the manifest, so the CI ownership checker remains independent and strict.
    seed.mkdir(parents=True); (seed/'files').mkdir()
    manifest=[]; total=0
    for index,(name,st,path) in enumerate(rows):
        kind='d' if stat.S_ISDIR(st.st_mode) else 'l' if stat.S_ISLNK(st.st_mode) else 'f'
        fields=[kind,str(st.st_uid),str(st.st_gid),format(st.st_mode&0o7777,'o'),name]
        if kind=='l':
            target=os.readlink(path)
            assert target and not any(c in target for c in '\t\r\n')
            fields.append(target)
        if kind=='f':
            data=path.read_bytes(); total+=len(data)
            assert len(data)<=1024*1024 and total<=1024*1024
            slot=f'{index:04}.bin'; (seed/'files'/slot).write_bytes(data); fields.append(slot)
        manifest.append('\t'.join(fields)+'\n')
    data=''.join(manifest).encode(); assert len(data)<65536
    (seed/'manifest.tsv').write_bytes(data)
    for directory,dirs,files in os.walk(seed):
        for path in [Path(directory)]+[Path(directory)/n for n in files]:
            path.chmod(0o755 if path.is_dir() else 0o644); os.chown(path,0,0)
    # Match HackiOS's temporary-file location on the writable data filesystem.
    tmp=root/'tmp'
    assert tmp.is_symlink() and os.readlink(tmp)=='private/tmp'
    tmp.unlink(); tmp.symlink_to('private/var/tmp'); os.lchown(tmp,0,0)
    print('M74 saved var records',len(rows),'seed file bytes',total,'manifest bytes',len(data))

if __name__=='__main__':stage(Path(sys.argv[1]))
