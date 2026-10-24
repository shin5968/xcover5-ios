/* M30: explicit, non-lazy libSystem imports. All media access is read-only.
 * mklibsystemprobe.py places _start at 0x800, pointer table at 0x4000.
 * Imports: getpid, strlen, memcmp, read, write. Raw syscalls are the oracle
 * for getpid and provide diagnostics/exit even if an imported call fails.
 */
.text
.globl _start
.p2align 2
_start:
start_anchor:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #256
 adr x23, start_anchor
 mov x9, #0x3800
 add x23, x23, x9
 mov x24, #101
 /* Every slot must have been bound before entering main. */
 mov x9, #0
slots:
 ldr x10, [x23, x9]
 cbz x10, failed
 add x9, x9, #8
 cmp x9, #40
 b.ne slots
 mov x0, #1
 adr x1, entered
 adr x2, entered_end
 sub x2, x2, x1
 mov x16, #4
 svc #0x80
 mov x24, #102
 mov x16, #20
 svc #0x80
 b.cs failed
 cmp x0, #1
 b.le failed
 mov x22, x0
 ldr x9, [x23]
 blr x9
 cmp w0, w22
 b.ne failed
 mov x24, #103
 adr x0, expected
 ldr x9, [x23, #8]
 blr x9
 adr x9, expected
 adr x10, expected_end
 sub x21, x10, x9
 cmp x0, x21
 b.ne failed
 /* A non-equal case catches a bogus memcmp that always returns zero. */
 mov x24, #104
 adr x0, expected
 adr x1, different
 mov x2, #1
 ldr x9, [x23, #16]
 blr x9
 cbz w0, failed
 mov x24, #105
 adr x0, proof
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov x24, #106
 mov x1, sp
 mov x2, #128
 ldr x9, [x23, #24]
 blr x9
 cmp x0, x21
 b.ne failed
 mov x24, #107
 mov x0, sp
 adr x1, expected
 mov x2, x21
 ldr x9, [x23, #16]
 blr x9
 cbnz w0, failed
 mov x0, x20
 mov x16, #6
 svc #0x80
 mov x24, #108
 mov x0, #1
 adr x1, message
 adr x2, message_end
 sub x2, x2, x1
 mov x21, x2
 ldr x9, [x23, #32]
 blr x9
 cmp x0, x21
 b.ne failed
 mov x0, #51
 b exit_now
failed:
 /* Exit 101..108 identifies the failing check; no fabricated PASS. */
 mov x0, x24
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
proof:
 .asciz "/emmc/m20-proof.txt"
expected:
 .ascii "XCOVER5 M20 eMMC file read verified\n"
expected_end:
 .byte 0
different:
 .asciz "!"
entered:
 .ascii "XCOVER5 M30 CHILD: entered main with five bound libSystem slots\n"
entered_end:
message:
 .ascii "XCOVER5 M30 CHILD PASS: libSystem getpid + strlen + memcmp + read + write\n"
message_end:
