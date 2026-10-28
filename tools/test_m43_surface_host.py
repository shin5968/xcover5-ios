"""Real macOS IOSurface cross-exec test; only earlier milestones are stubbed."""
from pathlib import Path
import os,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);stub=d/'baseline.c';stub.write_text('int m41_baseline_main(int argc,char **argv){(void)argc;(void)argv;return 63;}\n')
 exe=d/'surface-test'
 subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-DM43_HOST_TEST',str(r/'tools/surface-sharing.c'),str(stub),'-framework','CoreFoundation','-o',str(exe)],check=True)
 good=subprocess.run([str(exe)],text=True,capture_output=True,timeout=45)
 print(good.stdout,end='');print(good.stderr,end='')
 assert good.returncode==64,good.returncode
 assert good.stdout.count('M43 READER PASS')==2 and good.stdout.count('M43 GONE PASS')==2
 assert good.stdout.count('M43 ROUND PASS')==2 and 'XCOVER5 M43 PASS:' in good.stdout
 env=os.environ.copy();env['M43_TEST_CORRUPT']='1'
 bad=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=45)
 print(bad.stdout,end='');print(bad.stderr,end='')
 assert bad.returncode==215 and 'pixel_mismatch' in bad.stderr
 assert 'XCOVER5 M43 PASS:' not in bad.stdout
 print('M43 real host IOSurface: two exec readers, reverse write, released-ID rejection; corrupt pixel rejected PASS. Host Apple driver, not ported-kernel execution; M41 stub only.')

 # Hold before exec and before lookup; parent must retain distinct progress and fail216.
 for phase in (1,5):
  env=os.environ.copy();env['M46C_TEST_HOLD_PHASE']=str(phase)
  timed=subprocess.run([str(exe)],env=env,text=True,capture_output=True,timeout=30)
  assert timed.returncode==216,(phase,timed.returncode,timed.stderr)
  assert f'phase={phase} ' in timed.stderr and 'M46C TIMEOUT child=' in timed.stderr,timed.stderr
  assert 'XCOVER5 M43 PASS:' not in timed.stdout
 print('M46C progress channel across exec: pre-exec and pre-lookup timeout snapshots distinguished PASS.')
