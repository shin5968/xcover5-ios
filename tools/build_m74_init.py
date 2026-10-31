"""Redirect only the reviewed static init's final PID1 handoff to owned prep."""
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
old='m35_launchd: .asciz "/sbin/launchd.ios"'
new='m35_launchd: .asciz "/sbin/m74-var-init"'
assert source.count(old)==1 and new not in source
result=source.replace(old,new)
assert result.replace(new,old)==source
Path(sys.argv[2]).write_text(result)
