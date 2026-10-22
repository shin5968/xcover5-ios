#!/usr/bin/env python3
"""Pack a boot image into an Odin-flashable AP .tar.md5 (Samsung format).

usage: make_odin_tar.py boot.img out.tar.md5
Flash in Download mode: Odin -> AP -> out.tar.md5 (leave Auto Reboot as you like).
"""
import hashlib, sys, tarfile

src, out = sys.argv[1], sys.argv[2]
tar_path = out[:-4] if out.endswith(".md5") else out
with tarfile.open(tar_path, "w", format=tarfile.GNU_FORMAT) as t:
	ti = tarfile.TarInfo("boot.img")
	data = open(src, "rb").read()
	ti.size = len(data)
	ti.mode = 0o644
	import io
	t.addfile(ti, io.BytesIO(data))
h = hashlib.md5(open(tar_path, "rb").read()).hexdigest()
with open(tar_path, "ab") as f:
	f.write(("%s  %s\n" % (h, tar_path.split("/")[-1].split("\\")[-1])).encode())
import os
os.replace(tar_path, out if out.endswith(".md5") else tar_path)
print("wrote", out)
