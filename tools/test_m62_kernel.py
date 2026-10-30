"""Fail before compiling if the integrated runtime patch was skipped."""
from pathlib import Path
import sys
r=Path(sys.argv[1])
for name in ('bsd/kern/kern_minimac.c','libkern/amfi/miniamfi.c','libkern/amfi/miniamfi_entitlements.cpp'):
 s=(r/name).read_text();assert s.index('#include <pexpert/arm64/board_config.h>')<s.index('#if defined(XCOVER5)'),name
assert 'XCOVER5 M62 INJECT' in (r/'bsd/kern/kern_exec.c').read_text()
assert 'minimac_policy_init();' in (r/'osfmk/kern/startup.c').read_text()
assert '#if defined(ARM64_BOARD_CONFIG_SWEET) && !defined(XCOVER5)' in (r/'bsd/kern/sweet_amfi.c').read_text()
assert 'kern_minimac.c' in (r/'bsd/conf/files').read_text()
assert 'miniamfi_entitlements.cpp' in (r/'libkern/conf/files').read_text()
print('M62 all runtime patch files, provider selection, injection and startup hooks present PASS')
