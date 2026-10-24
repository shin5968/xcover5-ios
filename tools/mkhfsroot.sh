#!/bin/bash
# CI-only: isolated RAM-root image, no phone or host physical disk writes.
set -euo pipefail
INIT=${1:?INIT required}
OUT=${2:?OUT required}
PROBE=${3:?PROBE required}
DYNAMIC=${4:?DYNAMIC required}
LOADER=${5:?LOADER required}
MMAP=${6:?MMAP required}
CODE=${7:?CODE required}
COW=${8:?COW required}
SEGMENT=${9:?SEGMENT required}
LIBRARY=${10:?LIBRARY required}
SYMBOL=${11:?SYMBOL required}
SYMLIB=${12:?SYMLIB required}
APPLEAPP=${13:?APPLEAPP required}
APPLEPLACEHOLDER=${14:?APPLEPLACEHOLDER required}
CACHEPROBE=${15:?CACHEPROBE required}
CACHEDYLD=${16:?CACHEDYLD required}
LIBSYSTEM=${17:?LIBSYSTEM required}
THREAD=${18:?THREAD required}
MUTEX=${19:?MUTEX required}
IPC=${20:?IPC required}
PROCESSIPC=${21:?PROCESSIPC required}
LAUNCHDPROOF=${22:?LAUNCHDPROOF required}
BOOTSTRAP=${23:?BOOTSTRAP required}
WORK=$(mktemp -d)
cleanup() { hdiutil detach "$WORK/mnt" >/dev/null 2>&1 || true; }
trap cleanup EXIT
hdiutil create -size 16m -layout NONE -fs 'Case-sensitive HFS+' -volname XCOVER5TEST "$WORK/root.dmg" >/dev/null
hdiutil attach -owners on -nobrowse -mountpoint "$WORK/mnt" "$WORK/root.dmg" >/dev/null
sudo mkdir -p "$WORK/mnt/sbin" "$WORK/mnt/dev" "$WORK/mnt/private/var" "$WORK/mnt/emmc"
sudo cp "$INIT" "$WORK/mnt/sbin/launchd"
sudo chmod 755 "$WORK/mnt/sbin/launchd"
sudo cp "$PROBE" "$WORK/mnt/sbin/m21-probe"
sudo chmod 755 "$WORK/mnt/sbin/m21-probe"
sudo mkdir -p "$WORK/mnt/usr/lib"
sudo cp "$DYNAMIC" "$WORK/mnt/sbin/m22-probe"
sudo cp "$LOADER" "$WORK/mnt/usr/lib/m22-loader"
sudo chmod 755 "$WORK/mnt/sbin/m22-probe" "$WORK/mnt/usr/lib/m22-loader"
sudo cp "$MMAP" "$WORK/mnt/sbin/m23-probe"
sudo cp "$CODE" "$WORK/mnt/usr/lib/m23-code"
sudo chmod 755 "$WORK/mnt/sbin/m23-probe" "$WORK/mnt/usr/lib/m23-code"
sudo cp "$COW" "$WORK/mnt/sbin/m24-probe"
sudo chmod 755 "$WORK/mnt/sbin/m24-probe"
sudo cp "$SEGMENT" "$WORK/mnt/sbin/m25-probe"
sudo cp "$LIBRARY" "$WORK/mnt/usr/lib/libm25.dylib"
sudo chmod 755 "$WORK/mnt/sbin/m25-probe" "$WORK/mnt/usr/lib/libm25.dylib"
sudo cp "$SYMBOL" "$WORK/mnt/sbin/m26-probe"
sudo cp "$SYMLIB" "$WORK/mnt/usr/lib/libm26.dylib"
sudo chmod 755 "$WORK/mnt/sbin/m26-probe" "$WORK/mnt/usr/lib/libm26.dylib"
sudo cp "$APPLEAPP" "$WORK/mnt/sbin/m27-probe"
sudo cp "$APPLEPLACEHOLDER" "$WORK/mnt/usr/lib/m27-apple-dyld"
sudo chmod 755 "$WORK/mnt/sbin/m27-probe" "$WORK/mnt/usr/lib/m27-apple-dyld"
sudo mkdir -p "$WORK/mnt/System/Library/Caches/com.apple.dyld"
sudo cp "$CACHEPROBE" "$WORK/mnt/sbin/m28-probe"
sudo chmod 755 "$WORK/mnt/sbin/m28-probe"
sudo cp "$CACHEDYLD" "$WORK/mnt/sbin/m29-probe"
sudo chmod 755 "$WORK/mnt/sbin/m29-probe"
sudo cp "$LIBSYSTEM" "$WORK/mnt/sbin/m30-probe"
sudo chmod 755 "$WORK/mnt/sbin/m30-probe"
sudo cp "$THREAD" "$WORK/mnt/sbin/m31-probe"
sudo chmod 755 "$WORK/mnt/sbin/m31-probe"
sudo cp "$MUTEX" "$WORK/mnt/sbin/m32-probe"
sudo chmod 755 "$WORK/mnt/sbin/m32-probe"
sudo cp "$IPC" "$WORK/mnt/sbin/m33-probe"
sudo chmod 755 "$WORK/mnt/sbin/m33-probe"
sudo cp "$PROCESSIPC" "$WORK/mnt/sbin/m34-probe"
sudo chmod 755 "$WORK/mnt/sbin/m34-probe"
sudo python3 tools/stage_launchd.py "$WORK/mnt"
sudo cp "$LAUNCHDPROOF" "$WORK/mnt/sbin/m35-proof"
sudo chmod 755 "$WORK/mnt/sbin/m35-proof"
sudo cp "$BOOTSTRAP" "$WORK/mnt/sbin/m36-probe"
sudo chmod 755 "$WORK/mnt/sbin/m36-probe"
sudo chmod 644 "$WORK/mnt/System/Library/LaunchDaemons/org.xcover5.m36.echo.plist"
printf 'XCOVER5 M20 eMMC file read verified\n' | sudo tee "$WORK/mnt/m20-proof.txt" >/dev/null
echo 'XCOVER5 HFS root test' | sudo tee "$WORK/mnt/root-test.txt" >/dev/null
# Persist actual root ownership; host images otherwise inherit runner uid501.
sudo chown -hR 0:0 "$WORK/mnt"
sudo chown 501:501 "$WORK/mnt/private/var/mobile"
sudo chmod 644 "$WORK/mnt/System/Library/LaunchDaemons/org.xcover5.m35.proof.plist"
sync
hdiutil detach "$WORK/mnt" >/dev/null
hdiutil convert "$WORK/root.dmg" -format UDTO -o "$WORK/raw" >/dev/null
cp "$WORK/raw.cdr" "$OUT"
python3 - "$OUT" <<'PY'
import sys,struct
with open(sys.argv[1],'rb') as f:
 f.seek(1024);h=f.read(48)
assert h[:2] in (b'H+',b'HX'), 'not raw HFS+ at offset1024'
block,count=struct.unpack_from('>II',h,40)
assert block*count<=16*1024*1024
print('Raw HFS root verified:',sys.argv[1],block,count)
PY

python3 tools/check_hfs_owners.py "$OUT"
