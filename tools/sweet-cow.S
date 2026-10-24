/* M24: private RW data page, independent read-only view, mprotect and unmap.
 * Descriptor is O_RDONLY; all modifications are private memory only.
 */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #64
 mov w28, #121
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
 mov w28, #122
 adr x0, data_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov w28, #123
 mov x1, sp
 mov x2, #32
 mov x3, #0
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #32
 b.ne failed
 mov w28, #124
 mov x0, #0
 mov x1, #16384
 mov x2, #3 /* private READ|WRITE, never EXEC */
 mov x3, #2
 mov x4, x20
 mov x5, #0
 mov x16, #197
 svc #0x80
 b.cs failed
 mov x21, x0
 mov w28, #125
 mov x0, #0
 mov x1, #16384
 mov x2, #1 /* independent read-only view */
 mov x3, #2
 mov x4, x20
 mov x5, #0
 mov x16, #197
 svc #0x80
 b.cs failed
 mov x22, x0
 mov w28, #126
 mov x9, #0
compare:
 ldrb w10, [sp, x9]
 ldrb w11, [x21, x9]
 cmp w10, w11
 b.ne failed
 ldrb w11, [x22, x9]
 cmp w10, w11
 b.ne failed
 add x9, x9, #1
 cmp x9, #32
 b.ne compare
 ldr x23, [sp]
 eor x24, x23, #0xff
 str x24, [x21]
 ldr x9, [x21]
 cmp x9, x24
 b.ne failed
 ldr x9, [x22]
 cmp x9, x23
 b.ne failed
 mov w28, #127
 mov x0, x20
 add x1, sp, #32
 mov x2, #32
 mov x3, #0
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #32
 b.ne failed
 mov x9, #0
check_file:
 add x12, sp, #32
 ldrb w10, [sp, x9]
 ldrb w11, [x12, x9]
 cmp w10, w11
 b.ne failed
 add x9, x9, #1
 cmp x9, #32
 b.ne check_file
 mov w28, #128
 mov x0, x21
 mov x1, #16384
 mov x2, #1 /* seal private page read-only */
 mov x16, #74
 svc #0x80
 b.cs failed
 ldr x9, [x21]
 cmp x9, x24
 b.ne failed
 mov w28, #129
 mov x0, x21
 mov x1, #16384
 mov x16, #73
 svc #0x80
 b.cs failed
 mov x0, x22
 mov x1, #16384
 mov x16, #73
 svc #0x80
 b.cs failed
 mov x0, x20
 mov x16, #6
 svc #0x80
 mov w28, #130
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
 mov x0, #45
 b exit_now
failed:
 mov w0, w28
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
console:
 .asciz "/dev/console"
data_path:
 .asciz "/emmc/usr/lib/m23-code"
message:
 .ascii "XCOVER5 M24 CHILD PASS: private COW + original unchanged + mprotect + munmap\n"
message_end:
