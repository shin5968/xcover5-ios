#!/usr/bin/env python3
"""Minimal boot.img header v2 packer for the XCover5 shim (no external deps).

Layout / values copied from the stock boot.img of G525NKXSFEYL1
(see stock/unpacked/header.txt). Unlocked bootloader (orange state) does not
verify the AVB footer, so none is written.

usage: mkbootimg_v2.py KERNEL DTB OUT [--ramdisk FILE]
"""
import argparse, gzip, struct

PAGE = 2048
BASE = 0x10000000
OS_VERSION = 0x1C00019C		# stock value
CMDLINE = b"androidboot.hardware=s5e3830 androidboot.selinux=permissive loop.max_part=7"
PARTITION_SIZE = 46137344	# stock image file size = boot partition payload size


def pad(b, n=PAGE):
	return b + b"\0" * (-len(b) % n)


def empty_cpio_gz():
	# newc trailer only: a valid, empty initramfs
	name = b"TRAILER!!!\0"
	hdr = b"070701" + b"".join(b"%08X" % v for v in (0, 0o100000, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(name), 0))
	data = pad(hdr + name, 4)
	return gzip.compress(pad(data, 512))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("kernel"); ap.add_argument("dtb"); ap.add_argument("out")
	ap.add_argument("--ramdisk")
	a = ap.parse_args()
	kernel = open(a.kernel, "rb").read()
	dtb = open(a.dtb, "rb").read()
	ramdisk = open(a.ramdisk, "rb").read() if a.ramdisk else empty_cpio_gz()
	hdr = b"ANDROID!"
	hdr += struct.pack("<10I", len(kernel), BASE + 0x8000, len(ramdisk), BASE + 0x1000000,
			   0, BASE + 0xF00000, BASE + 0x100, PAGE, 2, OS_VERSION)
	hdr += b"SHIMXC5".ljust(16, b"\0") + CMDLINE.ljust(512, b"\0") + b"\0" * 32 + b"\0" * 1024
	k_pages = len(pad(kernel)) // PAGE
	r_pages = len(pad(ramdisk)) // PAGE
	rec_off = PAGE * (1 + k_pages + r_pages)
	hdr += struct.pack("<IQI", 0, rec_off, 1660)		# recovery_dtbo size/offset, header_size
	hdr += struct.pack("<IQ", len(dtb), BASE)		# dtb size/addr
	assert len(hdr) <= PAGE and 1660 <= len(hdr)
	img = pad(hdr) + pad(kernel) + pad(ramdisk) + pad(dtb)
	assert len(img) <= PARTITION_SIZE, "image bigger than boot partition"
	open(a.out, "wb").write(img)
	print("wrote %s (%d bytes, kernel %d, ramdisk %d, dtb %d)" % (a.out, len(img), len(kernel), len(ramdisk), len(dtb)))


main()
