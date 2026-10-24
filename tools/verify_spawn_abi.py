#!/usr/bin/env python3
"""Compile layout assertions from the actual XNU spawn struct, without SDK headers.
The scalar aliases below match XNU arm64 Darwin types; no Linux sigset_t is used.
Usage: verify_spawn_abi.py XNU_SOURCE OUTPUT_C
"""
from pathlib import Path
import sys
src, out = map(Path, sys.argv[1:])
s = (src/'bsd/sys/spawn_internal.h').read_text()
start = s.index('typedef struct _posix_spawnattr {')
end = s.index('_posix_spawn_port_actions_t    psa_ports;', start)
body = s[start:end].replace('typedef struct _posix_spawnattr {', 'struct spawn_prefix {')
body += 'void *psa_ports; };\n'
pre = '#include <stdint.h>\n#include <stddef.h>\n#include <stdbool.h>\n#define NBINPREFS 4\ntypedef uint32_t sigset_t;\ntypedef int32_t pid_t, cpu_type_t, cpu_subtype_t, task_role_t;\n'
checks = '_Static_assert(offsetof(struct spawn_prefix, psa_flags)==0, "flags");\n_Static_assert(offsetof(struct spawn_prefix, psa_platform)==108, "platform");\n_Static_assert(offsetof(struct spawn_prefix, psa_ports)==184, "copyin length");\n'
out.write_text(pre+body+checks)
print('Generated assertions from', src)
