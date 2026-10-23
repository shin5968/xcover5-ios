/*
 * First userspace program for SWEET bring-up: mockfs serves the RAM disk
 * itself as /sbin/launchd, so this static binary is PID 1. It proves that
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

tick:
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
