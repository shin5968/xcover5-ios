"""HackiOS mkjobs.py console/os_log recipe, adapted for the XCover5 RAM root.

Derived from OOSEX GANG hackios-xnu-userland a79ff0772a3454fd1ef127e181e5b3bce6c9ce18.
MIT license and exact upstream sources: third_party/hackios-userland/.
Only requested jobs receive os_log console routing; no extra daemons are enabled.
"""
from copy import deepcopy


def console_job(job, *, oslog=False):
    result = deepcopy(job)
    result['StandardErrorPath'] = '/dev/console'
    result['StandardOutPath'] = '/dev/console'
    if oslog:
        result.setdefault('EnvironmentVariables', {})['OS_ACTIVITY_DT_MODE'] = 'YES'
    return result
