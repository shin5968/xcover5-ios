"""M38: original libSystem notify API imports; no local notify implementation."""
from pathlib import Path
import sys
import mkinit, mklibsystemprobe
IMPORTS = (b'_notify_register_mach_port', b'_notify_post', b'_notify_cancel',
           b'_mach_msg', b'_notify_is_valid_token')
if __name__ == '__main__':
    Path(sys.argv[2]).write_bytes(mklibsystemprobe.build_code(
        *mkinit.text_of(Path(sys.argv[1]).read_bytes()), imports=IMPORTS))

