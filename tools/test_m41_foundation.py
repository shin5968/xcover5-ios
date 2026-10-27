"""Real Foundation runtime/RunLoop host test. M39/M40 are stubbed only here."""
from pathlib import Path
import os,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);stub=d/'baseline.c'
    stub.write_text('int m40_baseline_main(int argc,char **argv){(void)argc;(void)argv;return 62;}\n')
    binary=d/'m41-host'
    subprocess.run(['xcrun','clang','-DM41_HOST_TEST','-O1','-Wall','-Wextra','-Werror','-framework','CoreFoundation','-lobjc',str(r/'tools/foundation-runloop.c'),str(stub),'-o',str(binary)],check=True)
    for skip,expected in [(False,63),(True,196)]:
        env=os.environ.copy()
        if skip:env['M41_TEST_NO_SCHEDULE']='1'
        else:env.pop('M41_TEST_NO_SCHEDULE',None)
        p=subprocess.run([str(binary)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
        print(p.stdout)
        assert p.returncode==expected,(skip,p.returncode)
        if skip:
            assert 'where=timer_callbacks_or_thread_or_payload' in p.stdout
            assert 'XCOVER5 M41 PASS:' not in p.stdout
        else:
            assert p.stdout.count('M41 TIMER fired=')==3
            assert p.stdout.count('main_thread=1')==3
            for m in ['M41 OBJECTS PASS:', 'M41 RUNLOOP PASS:', 'invalidate=yes', 'M41 PASS:']:
                assert m in p.stdout,m
    print('M41 real host Foundation dynamic load, objects, three RunLoop timer callbacks, payload/thread, invalidation and unscheduled-timer rejection PASS; baseline stubbed only on host, not iOS proof.')
