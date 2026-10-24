/* M23: file-backed RX mmap, compare against pread, call and unmap.
 * All media access is read-only. Failure exit codes identify the stage.
 */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #64
 mov w28, #101
 mov x16, #20
 svc #0x80
 b.cs failed
 cmp x0, #1
 b.le failed
 adr x0, console
 mov x1, #2
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x19, x0
 mov w28, #102
 adr x0, code_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov w28, #103
 mov x1, sp
 mov x2, #32
 mov x3, #0
 mov x16, #153 /* pread */
 svc #0x80
 b.cs failed
 cmp x0, #32
 b.ne failed
 mov w28, #104
 mov x0, #0
 mov x1, #16384
 mov x2, #5 /* PROT_READ | PROT_EXEC; never writable */
 mov x3, #2 /* MAP_PRIVATE */
 mov x4, x20
 mov x5, #0
 mov x16, #197
 svc #0x80
 b.cs failed
 mov x21, x0
 mov w28, #105
 mov x9, sp
 mov x10, x21
 mov x11, #32
compare:
 ldrb w12, [x9], #1
 ldrb w13, [x10], #1
 cmp w12, w13
 b.ne failed
 subs x11, x11, #1
 b.ne compare
 mov w28, #106
 ldr w9, [x21]
 mov w10, #0xfacf
 movk w10, #0xfeed, lsl #16
 cmp w9, w10
 b.ne failed
 /* Code entry is fixed by mkinit.py's independently verified CODE_OFF. */
 add x9, x21, #1024
 blr x9
 cmp w0, #44
 b.ne failed
 mov w28, #107
 mov x0, x21
 mov x1, #16384
 mov x16, #73
 svc #0x80
 b.cs failed
 mov x0, x20
 mov x16, #6
 svc #0x80
 mov w28, #108
 mov x0, x19
 adr x1, message
 adr x2, message_end
 sub x2, x2, x1
 mov x22, x2
 mov x16, #4
 svc #0x80
 b.cs failed
 cmp x0, x22
 b.ne failed
 mov x0, #44
 b exit_now
failed:
 mov w0, w28
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
console:
 .asciz "/dev/console"
code_path:
 .asciz "/emmc/usr/lib/m23-code"
message:
 .ascii "XCOVER5 M23 CHILD PASS: eMMC RX mmap + function return + munmap\n"
message_end:
