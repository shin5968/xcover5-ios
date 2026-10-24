/*
 * Static userspace init for SWEET bring-up, installed in the HFS RAM root
 * as /sbin/launchd. It is a diagnostic PID 1, not Apple launchd. It proves that
 * exec, the user/kernel boundary, devfs and the console all work, then
 * stays alive (init exiting panics the kernel).
 *
 * tools/mkinit.py wraps the assembled __text into a static Mach-O, so this
 * must stay position independent with no relocations and no writable data:
 * every reference is adr (PC-relative), the PID digit lives on the stack.
 *
 * Raw XNU syscalls: number in x16, svc #0x80, carry set on error.
 */
#define SYS_write	4
#define SYS_open	5
#define SYS_getpid	20
#define SYS_select	93
#define O_RDWR		2

	.text
	.globl	_start
	.p2align 2
_start:
	/*
	 * The kernel enters a static binary with sp at argc, aligned only to
	 * what the argument/apple strings happened to need. Using a misaligned
	 * sp as a base register raises an SP alignment fault (SIGBUS) on real
	 * hardware (QEMU does not check), so align it like crt0/dyld do.
	 */
	mov	x9, sp
	and	x9, x9, #~15
	mov	sp, x9

	adr	x0, path
	mov	x1, #O_RDWR
	mov	x2, #0
	mov	x16, #SYS_open
	svc	#0x80
	b.cs	hang			/* no console: nothing to report to */
	mov	x19, x0

	adr	x1, hello
	adr	x2, hello_tail
	sub	x2, x2, x1
	bl	write_console

	mov	x16, #SYS_getpid
	svc	#0x80
	add	w0, w0, #'0'		/* PID 1 expected: one digit */
	sub	sp, sp, #16
	strb	w0, [sp]
	mov	x1, sp
	mov	x2, #1
	bl	write_console
	add	sp, sp, #16

	adr	x1, hello_tail
	adr	x2, alive
	sub	x2, x2, x1
	bl	write_console

 /* M18: read two sectors through devfs and verify MBR + GPT magic. */
 sub sp, sp, #1024
 adr x0, mmc_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs mmc_fail
 mov x20, x0
 mov x1, sp
 mov x2, #1024
 mov x16, #3
 svc #0x80
 b.cs mmc_close_fail
 cmp x0, #1024
 b.ne mmc_close_fail
 ldrh w9, [sp, #510]
 mov w10, #0xaa55
 cmp w9, w10
 b.ne mmc_close_fail
 ldr x9, [sp, #512]
 adr x10, gpt_magic
 ldr x10, [x10]
 cmp x9, x10
 b.ne mmc_close_fail
 mov x0, x20
 mov x16, #6
 svc #0x80
 adr x1, mmc_ok
 adr x2, mmc_ok_end
 b mmc_report
mmc_close_fail:
 mov x0, x20
 mov x16, #6
 svc #0x80
mmc_fail:
 adr x1, mmc_error
 adr x2, mmc_error_end
mmc_report:
 sub x2, x2, x1
 bl write_console
 add sp, sp, #1024
 bl m19_test
 bl m20_test
 cbz w0, tick /* Do not exec unless the eMMC mount/file proof succeeded. */
 bl m21_test
 bl m22_test
 bl m23_test
 bl m24_test
 bl m25_test
 bl m26_test

tick:
	/* Reap any late child after a timed-out M21; never block PID 1. */
	mov x0, #-1
	mov x1, #0
	mov x2, #1
	mov x3, #0
	mov x16, #7
	svc #0x80
	/* select(0, NULL, NULL, NULL, &5s) as a portable sleep */
	mov	x0, #0
	mov	x1, #0
	mov	x2, #0
	mov	x3, #0
	adr	x4, five_sec
	mov	x16, #SYS_select
	svc	#0x80

	adr	x1, alive
	adr	x2, alive_end
	sub	x2, x2, x1
	bl	write_console
	b	tick

/* write(x19, x1, x2) */
write_console:
	mov	x0, x19
	mov	x16, #SYS_write
	svc	#0x80
	ret

hang:
	b	hang

	.p2align 3
five_sec:
	.quad	5			/* tv_sec */
	.quad	0			/* tv_usec (int32 + padding) */
path:
	.asciz	"/dev/console"
hello:
	.ascii	"\n*** XCOVER5 userspace: init running as PID "
hello_tail:
	.ascii	" ***\n"
alive:
	.ascii	"XCOVER5 init: still alive\n"
alive_end:

mmc_path:
 .asciz "/dev/xcmmc"
gpt_magic:
 .ascii "EFI PART"
mmc_ok:
 .ascii "XCOVER5 M18 USER PASS: MBR + GPT via /dev/xcmmc\n"
mmc_ok_end:
mmc_error:
 .ascii "XCOVER5 M18 USER FAIL: open/read/signature\n"
mmc_error_end:

/* M19: bounded userspace partition reads. All storage opens are O_RDONLY.
 * Fixed supported GPT layout: 128 entries x128 bytes at LBA2, 512B sectors.
 * x19 console, x20 media fd, x21/x22 16KiB buffers, w28 diagnostic stage.
 * Helpers preserve x19-x28; no writable globals or external relocations.
 */
.p2align 2
m19_test:
 sub sp, sp, #8, lsl #12
 sub sp, sp, #16
 str x30, [sp]
 add x21, sp, #16
 add x22, x21, #4, lsl #12
 mov x20, #-1
 mov w28, #1
 adr x1, m19_start
 adr x2, m19_start_end
 sub x2, x2, x1
 bl write_console
 adr x0, mmc_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs m19_fail
 mov x20, x0
 mov w28, #2
 mov x1, x21
 mov x2, #1024
 mov x3, #0
 bl m19_pread
 cbnz w0, m19_fail
 ldrh w9, [x21, #510]
 mov w10, #0xaa55
 cmp w9, w10
 b.ne m19_fail
 add x12, x21, #512
 ldr x9, [x12]
 adr x10, gpt_magic
 ldr x10, [x10]
 cmp x9, x10
 b.ne m19_fail
 mov w28, #3
 ldr w9, [x12, #8]
 mov w10, #0x10000
 cmp w9, w10
 b.ne m19_fail
 ldr w1, [x12, #12]
 cmp w1, #92
 b.lo m19_fail
 cmp w1, #512
 b.hi m19_fail
 ldr w23, [x12, #16]
 str wzr, [x12, #16]
 mov x0, x12
 bl m19_crc32
 cmp w0, w23
 b.ne m19_fail
 add x12, x21, #512
 ldr x9, [x12, #24]
 cmp x9, #1
 b.ne m19_fail
 ldr x9, [x12, #72]
 cmp x9, #2
 b.ne m19_fail
 ldr w9, [x12, #80]
 cmp w9, #128
 b.ne m19_fail
 ldr w9, [x12, #84]
 cmp w9, #128
 b.ne m19_fail
 ldr x24, [x12, #40]
 ldr x25, [x12, #48]
 cmp x24, #34
 b.lo m19_fail
 cmp x25, x24
 b.lo m19_fail
 ldr x9, [x12, #32]
 cmp x9, x25
 b.ls m19_fail
 lsr x10, x9, #32
 cbnz x10, m19_fail
 ldr w23, [x12, #88]
 mov w28, #4
 mov x1, x21
 mov x2, #16384
 mov x3, #1024
 bl m19_pread
 cbnz w0, m19_fail
 mov x1, x22
 mov x2, #16384
 mov x3, #1024
 bl m19_pread
 cbnz w0, m19_fail
 bl m19_compare
 cbnz w0, m19_fail
 mov x0, x21
 mov x1, #16384
 bl m19_crc32
 cmp w0, w23
 b.ne m19_fail
 /* Locate exactly one occupied entry named UTF16 'boot'. Bounds validated
  * before shifting LBAs to byte offsets. No hard-coded boot start address. */
 mov w28, #5
 mov x26, #0
 mov x27, #0
 mov x12, x21
 mov w13, #128
m19_entry:
 ldp x9, x10, [x12]
 orr x9, x9, x10
 cbz x9, m19_entry_next
 ldr x9, [x12, #56]
 adr x10, m19_boot_name
 ldr x10, [x10]
 cmp x9, x10
 b.ne m19_entry_next
 ldrh w9, [x12, #64]
 cbnz w9, m19_entry_next
 cbnz x26, m19_fail
 ldp x26, x27, [x12, #32]
 cmp x26, x24
 b.lo m19_fail
 cmp x27, x26
 b.lo m19_fail
 cmp x27, x25
 b.hi m19_fail
m19_entry_next:
 add x12, x12, #128
 subs w13, w13, #1
 b.ne m19_entry
 cbz x26, m19_fail
 /* Supported Android v2 header, 2048B pages, bounded kernel+ramdisk. */
 mov w28, #6
 mov x1, x21
 mov x2, #512
 lsl x3, x26, #9
 bl m19_pread
 cbnz w0, m19_fail
 ldr x9, [x21]
 adr x10, m19_android
 ldr x10, [x10]
 cmp x9, x10
 b.ne m19_fail
 ldr w9, [x21, #40]
 cmp w9, #2
 b.ne m19_fail
 ldr w9, [x21, #36]
 cmp w9, #2048
 b.ne m19_fail
 ldr w9, [x21, #8]
 cbz w9, m19_fail
 add x24, x9, #2047
 and x24, x24, #0xfffffffffffff800
 add x24, x24, #2048
 sub x25, x27, x26
 add x25, x25, #1
 lsl x25, x25, #9
 cmp x24, x25
 b.hs m19_fail
 ldr w9, [x21, #16]
 cmp x9, #4, lsl #12
 b.lo m19_fail
 sub x10, x25, x24
 cmp x9, x10
 b.hi m19_fail
 add x24, x24, x26, lsl #9
 mov w28, #7
 mov x1, x21
 mov x2, #16384
 mov x3, x24
 bl m19_pread
 cbnz w0, m19_fail
 mov x1, x22
 mov x2, #16384
 mov x3, x24
 bl m19_pread
 cbnz w0, m19_fail
 bl m19_compare
 cbnz w0, m19_fail
 mov x0, x21
 mov x1, #16384
 bl m19_crc32
 mov w23, w0
 adr x1, m19_crc_msg
 adr x2, m19_crc_end
 sub x2, x2, x1
 bl write_console
 mov w0, w23
 bl m19_hex
 adr x1, m19_ok
 adr x2, m19_ok_end
 sub x2, x2, x1
 bl write_console
 b m19_finish
m19_fail:
 adr x1, m19_error
 adr x2, m19_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
m19_finish:
 cmp x20, #0
 b.lt m19_return
 mov x0, x20
 mov x16, #6
 svc #0x80
m19_return:
 ldr x30, [sp]
 add sp, sp, #16
 add sp, sp, #8, lsl #12
 ret

/* pread(fd=x20, buffer=x1, length=x2, byte offset=x3), exact read only. */
m19_pread:
 stp x2, x30, [sp, #-16]!
 mov x0, x20
 mov x16, #153
 svc #0x80
 b.cs m19_pread_bad
 ldr x9, [sp]
 cmp x0, x9
 b.ne m19_pread_bad
 mov w0, #0
 b m19_pread_done
m19_pread_bad:
 mov w0, #1
m19_pread_done:
 ldp x2, x30, [sp], #16
 ret

/* Compare two full 16KiB buffers, return 0 if identical. */
m19_compare:
 mov x9, #0
m19_compare_loop:
 ldr x10, [x21, x9]
 ldr x11, [x22, x9]
 cmp x10, x11
 b.ne m19_compare_bad
 add x9, x9, #8
 cmp x9, #4, lsl #12
 b.ne m19_compare_loop
 mov w0, #0
 ret
m19_compare_bad:
 mov w0, #1
 ret

/* Reflected IEEE CRC32 over x0,x1; return w0. */
m19_crc32:
 mov w9, #-1
 mov w10, #0x8320
 movk w10, #0xedb8, lsl #16
m19_crc_byte:
 ldrb w11, [x0], #1
 eor w9, w9, w11
 mov w12, #8
m19_crc_bit:
 and w13, w9, #1
 neg w13, w13
 lsr w9, w9, #1
 and w13, w13, w10
 eor w9, w9, w13
 subs w12, w12, #1
 b.ne m19_crc_bit
 subs x1, x1, #1
 b.ne m19_crc_byte
 mvn w0, w9
 ret

/* Print w0 as eight hex digits plus newline. */
m19_hex:
 sub sp, sp, #32
 str x30, [sp, #16]
 mov w9, w0
 mov x10, #0
 adr x11, m19_digits
m19_hex_loop:
 lsr w12, w9, #28
 ldrb w12, [x11, x12]
 strb w12, [sp, x10]
 lsl w9, w9, #4
 add x10, x10, #1
 cmp x10, #8
 b.ne m19_hex_loop
 mov w12, #10
 strb w12, [sp, #8]
 mov x1, sp
 mov x2, #9
 bl write_console
 ldr x30, [sp, #16]
 add sp, sp, #32
 ret

m19_boot_name:
 .short 0x62, 0x6f, 0x6f, 0x74
m19_android:
 .ascii "ANDROID!"
m19_digits:
 .ascii "0123456789abcdef"
m19_start:
 .ascii "XCOVER5 M19 USER: GPT CRC + boot partition read test\n"
m19_start_end:
m19_crc_msg:
 .ascii "XCOVER5 M19 USER: boot payload 16KiB CRC="
m19_crc_end:
m19_ok:
 .ascii "XCOVER5 M19 USER PASS: GPT CRC + boot header + 16KiB repeat\n"
m19_ok_end:
m19_error:
 .ascii "XCOVER5 M19 USER FAIL stage="
m19_error_end:

/* M20: mount the bounded eMMC-backed HFS view and read a known file. */
.p2align 2
m20_test:
 sub sp, sp, #256
 str x30, [sp]
 str wzr, [sp, #208]
 mov x20, #-1
 mov w28, #21
 stp xzr, xzr, [sp, #16]
 stp xzr, xzr, [sp, #32]
 stp xzr, xzr, [sp, #48]
 stp xzr, xzr, [sp, #64]
 adr x9, m20_device
 str x9, [sp, #16]
 mov w9, #493
 strh w9, [sp, #32]
 adr x0, m20_fstype
 adr x1, m20_mountpoint
 mov x2, #1 /* MNT_RDONLY */
 add x3, sp, #16
 mov x16, #167 /* mount */
 svc #0x80
 b.cs m20_sysfail
 adr x1, m20_mounted
 adr x2, m20_mounted_end
 sub x2, x2, x1
 bl write_console
 mov w28, #22
 adr x0, m20_file
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs m20_sysfail
 mov x20, x0
 mov w28, #23
 add x1, sp, #80
 mov x2, #128
 mov x16, #3
 svc #0x80
 b.cs m20_sysfail
 mov w28, #24
 mov w27, #0
 adr x9, m20_expected
 adr x10, m20_expected_end
 sub x10, x10, x9
 cmp x0, x10
 b.ne m20_fail
 add x11, sp, #80
m20_compare:
 ldrb w12, [x9], #1
 ldrb w13, [x11], #1
 cmp w12, w13
 b.ne m20_fail
 subs x10, x10, #1
 b.ne m20_compare
 mov w9, #1
 str w9, [sp, #208]
 adr x1, m20_ok
 adr x2, m20_ok_end
 sub x2, x2, x1
 bl write_console
 b m20_finish
m20_sysfail:
 mov w27, w0
m20_fail:
 adr x1, m20_error
 adr x2, m20_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m20_errno
 adr x2, m20_errno_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m20_finish:
 cmp x20, #0
 b.lt m20_return
 mov x0, x20
 mov x16, #6
 svc #0x80
m20_return:
 ldr w0, [sp, #208]
 ldr x30, [sp]
 add sp, sp, #256
 ret
m20_device:
 .asciz "/dev/xchfs"
m20_fstype:
 .asciz "hfs"
m20_mountpoint:
 .asciz "/emmc"
m20_file:
 .asciz "/emmc/m20-proof.txt"
m20_expected:
 .ascii "XCOVER5 M20 eMMC file read verified\n"
m20_expected_end:
m20_mounted:
 .ascii "XCOVER5 M20 USER: eMMC HFS mounted read-only at /emmc\n"
m20_mounted_end:
m20_ok:
 .ascii "XCOVER5 M20 USER PASS: file read from eMMC HFS\n"
m20_ok_end:
m20_error:
 .ascii "XCOVER5 M20 USER FAIL stage="
m20_error_end:
m20_errno:
 .ascii "XCOVER5 M20 errno="
m20_errno_end:

/* M21: fork/exec a separate static Mach-O from the read-only eMMC mount.
 * Darwin fork returns x1=1 in the child (x0 is NOT the libc zero result).
 * Bound WNOHANG polling; PID 1 must remain alive on every failure path.
 */
.p2align 2
m21_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #31
 adr x1, m21_start
 adr x2, m21_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m21_sysfail
 cbnz x1, m21_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #32
m21_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m21_wait_error
 cbz x0, m21_delay
 cmp x0, x20
 b.ne m21_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2a00 /* WIFEXITED && WEXITSTATUS == 42 */
 cmp w27, w9
 b.ne m21_bad_status
 adr x1, m21_ok
 adr x2, m21_ok_end
 sub x2, x2, x1
 bl write_console
 b m21_return
m21_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m21_sysfail
m21_delay:
 subs w21, w21, #1
 b.eq m21_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m21_wait
m21_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #34
 mov w27, #0
 b m21_fail
m21_bad_status:
 mov w28, #33
 ldr w27, [sp, #16]
 b m21_fail
m21_sysfail:
 mov w27, w0
m21_fail:
 adr x1, m21_error
 adr x2, m21_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m21_detail
 adr x2, m21_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m21_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m21_child:
 adr x0, m21_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #64] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #64
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m21_exec_error
 adr x2, m21_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m21_path:
 .asciz "/emmc/sbin/m21-probe"
m21_start:
 .ascii "XCOVER5 M21 USER: fork + exec /emmc/sbin/m21-probe\n"
m21_start_end:
m21_ok:
 .ascii "XCOVER5 M21 USER PASS: eMMC exec + child exit 42\n"
m21_ok_end:
m21_error:
 .ascii "XCOVER5 M21 USER FAIL stage="
m21_error_end:
m21_detail:
 .ascii "XCOVER5 M21 errno/status="
m21_detail_end:
m21_exec_error:
 .ascii "XCOVER5 M21 child exec errno="
m21_exec_error_end:

/* M22: same bounded process harness, separate dynamic image. */
.p2align 2
m22_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #41
 adr x1, m22_start
 adr x2, m22_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m22_sysfail
 cbnz x1, m22_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #42
m22_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m22_wait_error
 cbz x0, m22_delay
 cmp x0, x20
 b.ne m22_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2b00 /* WIFEXITED && WEXITSTATUS == 43 */
 cmp w27, w9
 b.ne m22_bad_status
 adr x1, m22_ok
 adr x2, m22_ok_end
 sub x2, x2, x1
 bl write_console
 b m22_return
m22_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m22_sysfail
m22_delay:
 subs w21, w21, #1
 b.eq m22_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m22_wait
m22_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #44
 mov w27, #0
 b m22_fail
m22_bad_status:
 mov w28, #43
 ldr w27, [sp, #16]
 b m22_fail
m22_sysfail:
 mov w27, w0
m22_fail:
 adr x1, m22_error
 adr x2, m22_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m22_detail
 adr x2, m22_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m22_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m22_child:
 adr x0, m22_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #64] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #64
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m22_exec_error
 adr x2, m22_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m22_path:
 .asciz "/emmc/sbin/m22-probe"
m22_start:
 .ascii "XCOVER5 M22 USER: fork + exec /emmc/sbin/m22-probe\n"
m22_start_end:
m22_ok:
 .ascii "XCOVER5 M22 USER PASS: loader handoff + dynamic child exit 43\n"
m22_ok_end:
m22_error:
 .ascii "XCOVER5 M22 USER FAIL stage="
m22_error_end:
m22_detail:
 .ascii "XCOVER5 M22 errno/status="
m22_detail_end:
m22_exec_error:
 .ascii "XCOVER5 M22 child exec errno="
m22_exec_error_end:

/* M23: same bounded process harness, separate dynamic image. */
.p2align 2
m23_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #51
 adr x1, m23_start
 adr x2, m23_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m23_sysfail
 cbnz x1, m23_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #52
m23_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m23_wait_error
 cbz x0, m23_delay
 cmp x0, x20
 b.ne m23_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2c00 /* WIFEXITED && WEXITSTATUS == 44 */
 cmp w27, w9
 b.ne m23_bad_status
 adr x1, m23_ok
 adr x2, m23_ok_end
 sub x2, x2, x1
 bl write_console
 b m23_return
m23_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m23_sysfail
m23_delay:
 subs w21, w21, #1
 b.eq m23_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m23_wait
m23_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #54
 mov w27, #0
 b m23_fail
m23_bad_status:
 mov w28, #53
 ldr w27, [sp, #16]
 b m23_fail
m23_sysfail:
 mov w27, w0
m23_fail:
 adr x1, m23_error
 adr x2, m23_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m23_detail
 adr x2, m23_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m23_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m23_child:
 adr x0, m23_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #64] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #64
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m23_exec_error
 adr x2, m23_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m23_path:
 .asciz "/emmc/sbin/m23-probe"
m23_start:
 .ascii "XCOVER5 M23 USER: fork + exec /emmc/sbin/m23-probe\n"
m23_start_end:
m23_ok:
 .ascii "XCOVER5 M23 USER PASS: RX file mapping + child exit 44\n"
m23_ok_end:
m23_error:
 .ascii "XCOVER5 M23 USER FAIL stage="
m23_error_end:
m23_detail:
 .ascii "XCOVER5 M23 errno/status="
m23_detail_end:
m23_exec_error:
 .ascii "XCOVER5 M23 child exec errno="
m23_exec_error_end:

/* M24: same bounded process harness, private data mapping probe. */
.p2align 2
m24_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #61
 adr x1, m24_start
 adr x2, m24_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m24_sysfail
 cbnz x1, m24_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #62
m24_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m24_wait_error
 cbz x0, m24_delay
 cmp x0, x20
 b.ne m24_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2d00 /* WIFEXITED && WEXITSTATUS == 45 */
 cmp w27, w9
 b.ne m24_bad_status
 adr x1, m24_ok
 adr x2, m24_ok_end
 sub x2, x2, x1
 bl write_console
 b m24_return
m24_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m24_sysfail
m24_delay:
 subs w21, w21, #1
 b.eq m24_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m24_wait
m24_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #64
 mov w27, #0
 b m24_fail
m24_bad_status:
 mov w28, #63
 ldr w27, [sp, #16]
 b m24_fail
m24_sysfail:
 mov w27, w0
m24_fail:
 adr x1, m24_error
 adr x2, m24_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m24_detail
 adr x2, m24_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m24_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m24_child:
 adr x0, m24_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #64] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #64
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m24_exec_error
 adr x2, m24_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m24_path:
 .asciz "/emmc/sbin/m24-probe"
m24_start:
 .ascii "XCOVER5 M24 USER: fork + exec /emmc/sbin/m24-probe\n"
m24_start_end:
m24_ok:
 .ascii "XCOVER5 M24 USER PASS: private COW + protection + child exit 45\n"
m24_ok_end:
m24_error:
 .ascii "XCOVER5 M24 USER FAIL stage="
m24_error_end:
m24_detail:
 .ascii "XCOVER5 M24 errno/status="
m24_detail_end:
m24_exec_error:
 .ascii "XCOVER5 M24 child exec errno="
m24_exec_error_end:

/* M25: same bounded process harness, private data mapping probe. */
.p2align 2
m25_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #71
 adr x1, m25_start
 adr x2, m25_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m25_sysfail
 cbnz x1, m25_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #72
m25_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m25_wait_error
 cbz x0, m25_delay
 cmp x0, x20
 b.ne m25_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2e00 /* WIFEXITED && WEXITSTATUS == 46 */
 cmp w27, w9
 b.ne m25_bad_status
 adr x1, m25_ok
 adr x2, m25_ok_end
 sub x2, x2, x1
 bl write_console
 b m25_return
m25_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m25_sysfail
m25_delay:
 subs w21, w21, #1
 b.eq m25_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m25_wait
m25_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #74
 mov w27, #0
 b m25_fail
m25_bad_status:
 mov w28, #73
 ldr w27, [sp, #16]
 b m25_fail
m25_sysfail:
 mov w27, w0
m25_fail:
 adr x1, m25_error
 adr x2, m25_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m25_detail
 adr x2, m25_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m25_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m25_child:
 adr x0, m25_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #74] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #74
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m25_exec_error
 adr x2, m25_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m25_path:
 .asciz "/emmc/sbin/m25-probe"
m25_start:
 .ascii "XCOVER5 M25 USER: fork + exec /emmc/sbin/m25-probe\n"
m25_start_end:
m25_ok:
 .ascii "XCOVER5 M25 USER PASS: segment rebase + child exit 46\n"
m25_ok_end:
m25_error:
 .ascii "XCOVER5 M25 USER FAIL stage="
m25_error_end:
m25_detail:
 .ascii "XCOVER5 M25 errno/status="
m25_detail_end:
m25_exec_error:
 .ascii "XCOVER5 M25 child exec errno="
m25_exec_error_end:

/* M26: same bounded process harness, private data mapping probe. */
.p2align 2
m26_test:
 sub sp, sp, #96
 str x30, [sp]
 mov w28, #81
 adr x1, m26_start
 adr x2, m26_start_end
 sub x2, x2, x1
 bl write_console
 mov x16, #2 /* fork */
 svc #0x80
 b.cs m26_sysfail
 cbnz x1, m26_child
 mov x20, x0 /* exact child PID, never wait for an unrelated process */
 mov w21, #100 /* at most 100 x 100ms waits */
 mov w28, #82
m26_wait:
 str wzr, [sp, #16]
 mov x0, x20
 add x1, sp, #16
 mov x2, #1 /* WNOHANG */
 mov x3, #0
 mov x16, #7 /* wait4 */
 svc #0x80
 b.cs m26_wait_error
 cbz x0, m26_delay
 cmp x0, x20
 b.ne m26_bad_status
 ldr w27, [sp, #16]
 mov w9, #0x2f00 /* WIFEXITED && WEXITSTATUS == 47 */
 cmp w27, w9
 b.ne m26_bad_status
 adr x1, m26_ok
 adr x2, m26_ok_end
 sub x2, x2, x1
 bl write_console
 b m26_return
m26_wait_error:
 cmp w0, #4 /* EINTR still consumes a bounded retry */
 b.ne m26_sysfail
m26_delay:
 subs w21, w21, #1
 b.eq m26_timeout
 stp xzr, xzr, [sp, #32]
 mov w9, #34464
 movk w9, #1, lsl #16 /* timeval.tv_usec = 100000 */
 str w9, [sp, #40]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #32
 mov x16, #93
 svc #0x80
 b m26_wait
m26_timeout:
 mov x0, x20
 mov x1, #9 /* SIGKILL; the created child only */
 mov x2, #1
 mov x16, #37
 svc #0x80
 /* The alive loop reaps this child if termination is not immediate. */
 mov w28, #84
 mov w27, #0
 b m26_fail
m26_bad_status:
 mov w28, #83
 ldr w27, [sp, #16]
 b m26_fail
m26_sysfail:
 mov w27, w0
m26_fail:
 adr x1, m26_error
 adr x2, m26_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w28
 bl m19_hex
 adr x1, m26_detail
 adr x2, m26_detail_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
m26_return:
 ldr x30, [sp]
 add sp, sp, #96
 ret
m26_child:
 adr x0, m26_path
 stp x0, xzr, [sp, #48] /* argv = { path, NULL } */
 str xzr, [sp, #84] /* envp = { NULL } */
 add x1, sp, #48
 add x2, sp, #84
 mov x16, #59 /* execve: success never returns */
 svc #0x80
 mov w27, w0
 adr x1, m26_exec_error
 adr x2, m26_exec_error_end
 sub x2, x2, x1
 bl write_console
 mov w0, w27
 bl m19_hex
 mov x0, #127
 mov x16, #1 /* child only: exit */
 svc #0x80
 b hang
m26_path:
 .asciz "/emmc/sbin/m26-probe"
m26_start:
 .ascii "XCOVER5 M26 USER: fork + exec /emmc/sbin/m26-probe\n"
m26_start_end:
m26_ok:
 .ascii "XCOVER5 M26 USER PASS: symbol binding + child exit 47\n"
m26_ok_end:
m26_error:
 .ascii "XCOVER5 M26 USER FAIL stage="
m26_error_end:
m26_detail:
 .ascii "XCOVER5 M26 errno/status="
m26_detail_end:
m26_exec_error:
 .ascii "XCOVER5 M26 child exec errno="
m26_exec_error_end:
