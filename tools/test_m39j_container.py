from pathlib import Path
import subprocess,sys,tempfile
r=Path(__file__).resolve().parents[1]
patch=(r/'xnu/patches/0061-xcover5-hackios-container-query.patch').read_text()
body=patch.split('+++ b/security/xcover5_prefs_container.h\n',1)[1]
header=''.join(line[1:] for line in body.splitlines(True) if line.startswith('+'))
if len(sys.argv)>1:
    tree=Path(sys.argv[1]);assert (tree/'security/xcover5_prefs_container.h').read_text()==header
    assert 'error = xcover5_prefs_container_path(p, uap->arg);' in (tree/'security/mac_base.c').read_text()
with tempfile.TemporaryDirectory() as d:
    d=Path(d);(d/'container.h').write_text(header)
    subprocess.run(['cc','-std=c11','-D_DEFAULT_SOURCE','-Wall','-Wextra','-Werror','-I'+str(d),str(r/'tools/test_m39j_container.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
