"""M34 cross-process Mach IPC probe with standard libSystem imports."""
from pathlib import Path
import sys
import mkinit,mklibsystemprobe
IMPORTS=(b'_mach_task_self_',b'_mach_port_allocate',b'_mach_port_insert_right',b'_mach_msg',b'_mach_port_destroy',b'_task_get_special_port',b'_task_set_special_port',b'_mach_port_deallocate',b'_fork',b'_waitpid',b'_getpid',b'_kill')
def build_code(code,start=0):
 return mklibsystemprobe.build_code(code,start,imports=IMPORTS)
if __name__=='__main__':
 Path(sys.argv[2]).write_bytes(build_code(*mkinit.text_of(Path(sys.argv[1]).read_bytes())))
