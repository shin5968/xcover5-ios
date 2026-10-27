"""Host dyld calibration only, no preference service or target execution."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)
 subprocess.run(['cc','-fblocks','-Wall','-Wextra','-Werror','-dynamiclib','-install_name',str(d/'libcal.dylib'),str(r/'m39s-calibration.c'),'-o',str(d/'libcal.dylib')],check=True)
 (d/'main.c').write_text('#include <stdatomic.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <errno.h>\n#include <assert.h>\n#include "m39s-observer-api.h"\nint main(void){assert(m39s_calibrate()==1);assert(m39s_calibration_count()==1);m39s_dump();puts("M39S native dyld cross-image calibration PASS (host only)");}\n')
 subprocess.run(['cc','-fblocks','-Wall','-Wextra','-Werror','-I',str(r),str(d/'main.c'),str(d/'libcal.dylib'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
