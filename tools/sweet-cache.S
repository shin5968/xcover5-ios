/* M28: bounded read-only cache inventory, not a dyld runtime success test. */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #1, lsl #12
 mov w28, #180
 mov x16, #20
 svc #0x80
 cmp x0, #1
 b.le failed
 adr x0, console
 mov x1, #2
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x19, x0
 adr x25, cache_records
 mov x26, #0
next_file:
 mov w28, #181
 add x0, x25, #16
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov w28, #182
 mov x1, #0
 mov x2, #2 /* SEEK_END: verify exact file length, no data write */
 mov x16, #199
 svc #0x80
 b.cs failed
 ldr x21, [x25]
 cmp x0, x21
 b.ne failed
 mov w28, #183
 mov x0, x20
 mov x1, sp
 mov x2, #4096
 mov x3, #0
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #1, lsl #12
 b.ne failed
 adr x9, magic
 ldp x10, x11, [x9]
 ldp x12, x13, [sp]
 cmp x10, x12
 b.ne failed
 cmp x11, x13
 b.ne failed
 mov x0, sp
 mov x1, #4096
 bl crc32
 mov w28, #184
 ldr w9, [x25, #8]
 cmp w0, w9
 b.ne failed
 mov w28, #185
 mov x0, x20
 mov x1, sp
 mov x2, #4096
 sub x3, x21, #1, lsl #12
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #1, lsl #12
 b.ne failed
 mov x0, sp
 mov x1, #4096
 bl crc32
 mov w28, #186
 ldr w9, [x25, #12]
 cmp w0, w9
 b.ne failed
 mov x0, x20
 mov x16, #6
 svc #0x80
 add x26, x26, #1
 add x25, x25, #16
skip_name:
 ldrb w9, [x25], #1
 cbnz w9, skip_name
 add x25, x25, #7
 and x25, x25, #~7
 adr x9, cache_records_end
 cmp x25, x9
 b.lo next_file
 b.ne failed
 cmp x26, #43
 b.ne failed
 mov x0, x19
 adr x1, passed
 adr x2, passed_end
 sub x2, x2, x1
 mov x16, #4
 svc #0x80
 b.cs failed
 mov x0, #49
 b exit_now
failed:
 /* Parent reports exit status; no file mutation on any path. */
 mov w0, w28
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
crc32:
 mov w9, #-1
 mov w10, #0x8320
 movk w10, #0xedb8, lsl #16
crc_byte:
 ldrb w11, [x0], #1
 eor w9, w9, w11
 mov w12, #8
crc_bit:
 and w13, w9, #1
 neg w13, w13
 lsr w9, w9, #1
 and w13, w13, w10
 eor w9, w9, w13
 subs w12, w12, #1
 b.ne crc_bit
 subs x1, x1, #1
 b.ne crc_byte
 mvn w0, w9
 ret
console:
 .asciz "/dev/console"
magic:
 .ascii "dyld_v1   arm64\0"
passed:
 .ascii "XCOVER5 M28 CHILD PASS: 43 cache files size + head/tail CRC verified\n"
passed_end:
#include "cache-records.inc"
