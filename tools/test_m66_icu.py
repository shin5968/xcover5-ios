"""Exercise real staging guards and the observer's NULL/failure paths with owned mocks."""
from pathlib import Path
import os
import subprocess
import tempfile
import stage_m66_icu as icu

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    icu.stage_root(root)
    for name in icu.FILES:
        assert os.readlink(root / 'usr/share/icu' / name) == icu.CACHE + name
    try:
        icu.stage_root(root)
    except ValueError:
        pass
    else:
        raise AssertionError('existing ICU links were overwritten')
    outside = root / 'outside'
    outside.mkdir()
    (root / 'usr/share/escape').symlink_to(outside, target_is_directory=True)
    try:
        icu.safe_path(root, '/usr/share/escape/new')
    except ValueError:
        pass
    else:
        raise AssertionError('symlink write path accepted')
    old = icu.FILES
    try:
        icu.FILES = {'owned.dat': (4099, 'unused')}
        icu.stage_cache(root)
        assert (root / 'owned.dat').read_bytes() == icu.block('owned.dat') + icu.block('owned.dat')[:3]
    finally:
        icu.FILES = old
    probe = Path(__file__).with_name('m66-icu-probe.h').read_text().replace('#include <CoreFoundation/CoreFoundation.h>', '')
    prefix = r'''
#include <stdio.h>
#include <sys/stat.h>
#include <errno.h>
#include <assert.h>
#include <stdlib.h>
typedef const void *CFLocaleRef; typedef const void *CFDateFormatterRef;
typedef const void *CFTimeZoneRef; typedef const void *CFStringRef;
#define CFSTR(x) ((const void *)(x))
#define kCFAllocatorDefault NULL
#define kCFDateFormatterShortStyle 1
#define kCFDateFormatterTimeZone NULL
#define kCFStringEncodingUTF8 1
static int mode,sets,releases;
static CFLocaleRef CFLocaleCreate(const void*a,const void*b){(void)a;(void)b;return mode==3?NULL:(void*)1;}
static CFDateFormatterRef CFDateFormatterCreate(const void*a,const void*b,int c,int d){(void)a;(void)b;(void)c;(void)d;return mode==0?NULL:(void*)2;}
static CFTimeZoneRef CFTimeZoneCreateWithTimeIntervalFromGMT(const void*a,int b){(void)a;(void)b;return (void*)3;}
static void CFDateFormatterSetProperty(const void*a,const void*b,const void*c){assert(a&&c);(void)b;}
static void CFDateFormatterSetFormat(const void*a,const void*b){assert(a&&b);sets++;}
static CFStringRef CFDateFormatterCreateStringWithAbsoluteTime(const void*a,const void*b,int c){(void)a;(void)c;assert(b);return mode==2?NULL:(void*)4;}
static int CFStringGetCString(const void*a,char*b,long c,int d){assert(a);(void)c;(void)d;sprintf(b,"2001-01-01 00:00:00");return 1;}
static void CFRelease(const void*a){assert(a);releases++;}
'''
    source = root / 'probe.c'
    source.write_text(prefix + probe + '\nint main(int n,char**v){assert(n==2);mode=atoi(v[1]);m66_icu_probe();assert(sets==(mode!=0));assert(releases==(mode==0?1:mode==2||mode==3?3:4));return 0;}\n')
    executable = root / 'probe'
    subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
    for mode in range(4):
        result = subprocess.run([str(executable), str(mode)], check=True, capture_output=True, text=True).stdout
        assert ('pass=1' in result) == (mode in (1,3))
        if mode == 0:
            assert 'DATE create=0' in result and 'DATE text=' not in result
print('M66 symlink destinations, unsafe-path/overwrite rejection, placeholder tail and NULL/create/format failure guards PASS; native CF/ICU execution remains a hardware check')
