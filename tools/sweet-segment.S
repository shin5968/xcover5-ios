/* M25 restricted own-library segment mapping + one pointer rebase.
 * Header must exactly match the fixture emitted by mksegment.py.
 * This is not a general Mach-O parser, import binder or Apple dyld.
 */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #528
 mov w28, #141
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
 mov w28, #142
 adr x0, library_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov w28, #143
 mov x1, sp
 mov x2, #512
 mov x3, #0
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #512
 b.ne failed
 mov w28, #144
 mov x9, sp
 adr x10, expected_layout
 mov x11, #512
check_layout:
 ldrb w12, [x9], #1
 ldrb w13, [x10], #1
 cmp w12, w13
 b.ne failed
 subs x11, x11, #1
 b.ne check_layout
 mov w28, #145
 mov x0, #0
 mov x1, #16384
 mov x2, #5 /* __TEXT READ|EXEC */
 mov x3, #2
 mov x4, x20
 mov x5, #0
 mov x16, #197
 svc #0x80
 b.cs failed
 mov x21, x0
 mov w28, #146
 mov x0, #0
 mov x1, #16384
 mov x2, #3 /* __DATA private READ|WRITE */
 mov x3, #2
 mov x4, x20
 mov x5, #16384
 mov x16, #197
 svc #0x80
 b.cs failed
 mov x22, x0
 mov w28, #147
 mov x23, #1024
 movk x23, #1, lsl #32 /* preferred function address */
 ldr x9, [x22]
 cmp x9, x23
 b.ne failed
 /* This fixture has exactly one known pointer in __DATA at offset0. */
 sub x9, x9, x23
 add x9, x9, x21
 add x9, x9, #1024
 str x9, [x22]
 mov w28, #148
 mov x0, x22
 mov x1, #16384
 mov x2, #1 /* seal relocated data read-only before call */
 mov x16, #74
 svc #0x80
 b.cs failed
 mov w28, #149
 ldr x9, [x22]
 blr x9
 cmp w0, #46
 b.ne failed
 mov w28, #150
 mov x0, x20
 add x1, sp, #512
 mov x2, #8
 mov x3, #16384
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #8
 b.ne failed
 ldr x9, [sp, #512]
 cmp x9, x23
 b.ne failed
 mov w28, #151
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
 mov w28, #152
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
 mov x0, #46
 b exit_now
failed:
 mov w0, w28
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
console:
 .asciz "/dev/console"
library_path:
 .asciz "/emmc/usr/lib/libm25.dylib"
message:
 .ascii "XCOVER5 M25 CHILD PASS: RX text + private data + pointer rebase + call46\n"
message_end:
expected_layout:
 .byte 207,250,237,254,12,0,0,1,0,0,0,0,6,0,0,0
 .byte 5,0,0,0,32,1,0,0,133,0,0,0,0,0,0,0
 .byte 25,0,0,0,72,0,0,0,95,95,84,69,88,84,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,64,0,0,0,0,0,0,5,0,0,0,5,0,0,0
 .byte 0,0,0,0,0,0,0,0,25,0,0,0,72,0,0,0
 .byte 95,95,68,65,84,65,0,0,0,0,0,0,0,0,0,0
 .byte 0,64,0,0,1,0,0,0,0,64,0,0,0,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,64,0,0,0,0,0,0
 .byte 3,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0
 .byte 25,0,0,0,72,0,0,0,95,95,76,73,78,75,69,68
 .byte 73,84,0,0,0,0,0,0,0,128,0,0,1,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,128,0,0,0,0,0,0
 .byte 123,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0
 .byte 0,0,0,0,0,0,0,0,13,0,0,0,56,0,0,0
 .byte 24,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0
 .byte 47,101,109,109,99,47,117,115,114,47,108,105,98,47,108,105
 .byte 98,109,50,53,46,100,121,108,105,98,0,0,0,0,0,0
 .byte 29,0,0,0,16,0,0,0,0,128,0,0,123,1,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
