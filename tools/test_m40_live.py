"""Real macOS CFPreferences + notifyd host integration. Not iOS hardware proof."""
from pathlib import Path
import os,re,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);stub=d/'baseline.c'
    stub.write_text('int m39_baseline_main(int argc,char **argv){(void)argc;(void)argv;return 60;}\n')
    binary=d/'m40-host'
    subprocess.run(['xcrun','clang','-DM40_HOST_TEST','-O1','-Wall','-Wextra','-Werror','-framework','CoreFoundation',str(r/'tools/preferences-live.c'),str(stub),'-o',str(binary)],check=True)
    for skip,expected in [(False,62),(True,179)]:
        env=os.environ.copy()
        if skip:env['M40_TEST_SKIP_POST']='1'
        else:env.pop('M40_TEST_SKIP_POST',None)
        p=subprocess.run([str(binary)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40)
        print(p.stdout)
        assert p.returncode==expected,(skip,p.returncode)
        if skip:
            assert 'where=notify_delivery_timeout' in p.stdout
            assert 'XCOVER5 M40 PASS:' not in p.stdout
        else:
            for marker in ['cached=A','cached=B without explicit sync','cached key absent without explicit sync','M40 READER PASS:','M40 PASS:']:
                assert marker in p.stdout,marker
    print('M40 real host CFPreferences + notifyd: live A/B/delete, cancellation, child exit, and missing-post rejection PASS. Baseline stubbed only on host; no iOS hardware claim.')
