/* M26 restricted own-library LC_SYMTAB lookup and binding.
 * Segment/header prefix must match mksymbol.py; symbol tables are parsed.
 * This is not a general Mach-O parser, import binder or Apple dyld.
 */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #1536
 mov w28, #161
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
 mov w28, #162
 adr x0, library_path
 mov x1, #0
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov w28, #163
 mov x1, sp
 mov x2, #1024
 mov x3, #0
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #1024
 b.ne failed
 mov w28, #164
 mov x9, sp
 adr x10, expected_layout
 mov x11, #328
check_layout:
 ldrb w12, [x9], #1
 ldrb w13, [x10], #1
 cmp w12, w13
 b.ne failed
 subs x11, x11, #1
 b.ne check_layout
 mov w28, #165
 /* Bounded LC_SYMTAB lookup; the segment layout above is fixture-specific. */
 ldr w9, [sp, #16]
 ldr w10, [sp, #20]
 add x11, sp, #32
 mov x24, #0
commands:
 cmp w10, #8
 b.lo failed
 ldp w12, w13, [x11]
 cmp w13, #8
 b.lo failed
 tst w13, #7
 b.ne failed
 cmp w13, w10
 b.hi failed
 cmp w12, #2
 b.ne next_command
 cbnz x24, failed
 cmp w13, #24
 b.ne failed
 ldp w24, w25, [x11, #8]
 ldp w26, w27, [x11, #16]
next_command:
 sub w10, w10, w13
 add x11, x11, x13
 subs w9, w9, #1
 b.ne commands
 cbnz w10, failed
 mov w28, #166
 cbz x25, failed
 cmp x25, #8
 b.hi failed
 cmp x24, #8, lsl #12
 b.lo failed
 lsl x9, x25, #4
 add x9, x24, x9
 cmp x9, #9, lsl #12
 b.hi failed
 cmp x26, x9
 b.lo failed
 cbz x27, failed
 cmp x27, #256
 b.hi failed
 add x9, x26, x27
 cmp x9, #9, lsl #12
 b.hi failed
 mov w28, #167
 mov x0, x20
 add x1, sp, #1024
 lsl x2, x25, #4
 mov x3, x24
 mov x16, #153
 svc #0x80
 b.cs failed
 lsl x9, x25, #4
 cmp x0, x9
 b.ne failed
 mov w28, #168
 mov x0, x20
 add x1, sp, #1152
 mov x2, x27
 mov x3, x26
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, x27
 b.ne failed
 mov w28, #169
 mov x23, #0
 add x10, sp, #1024
symbol_loop:
 ldr w11, [x10]
 cmp x11, x27
 b.hs failed
 add x12, sp, #1152
 adr x13, wanted_symbol
name_loop:
 cmp x11, x27
 b.hs failed
 ldrb w14, [x12, x11]
 ldrb w15, [x13], #1
 cmp w14, w15
 b.ne next_symbol
 add x11, x11, #1
 cbnz w14, name_loop
 cbnz x23, failed /* ambiguous duplicate */
 ldrb w14, [x10, #4]
 cmp w14, #15 /* N_SECT | N_EXT */
 b.ne failed
 ldrb w14, [x10, #5]
 cmp w14, #1 /* __TEXT,__text */
 b.ne failed
 ldr x23, [x10, #8]
 mov x14, #1
 lsl x14, x14, #32
 sub x14, x23, x14
 cmp x14, #1024
 b.lo failed
 cmp x14, #1048 /* end of fixture's __text section */
 b.hs failed
 tst x14, #3
 b.ne failed
next_symbol:
 add x10, x10, #16
 subs x25, x25, #1
 b.ne symbol_loop
 cbz x23, failed
 mov w28, #170
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
 mov w28, #171
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
 mov w28, #172
 ldr x9, [x22]
 cbnz x9, failed /* unresolved data slot starts at zero */
 mov x9, #1
 lsl x9, x9, #32
 sub x9, x23, x9
 add x9, x9, x21
 str x9, [x22] /* bind named symbol to runtime text address */
 mov w28, #173
 mov x0, x22
 mov x1, #16384
 mov x2, #1 /* seal relocated data read-only before call */
 mov x16, #74
 svc #0x80
 b.cs failed
 mov w28, #174
 ldr x9, [x22]
 blr x9
 cmp w0, #47
 b.ne failed
 mov w28, #175
 mov x0, x20
 add x1, sp, #1408
 mov x2, #8
 mov x3, #16384
 mov x16, #153
 svc #0x80
 b.cs failed
 cmp x0, #8
 b.ne failed
 ldr x9, [sp, #1408]
 cbnz x9, failed
 mov w28, #176
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
 mov w28, #177
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
 mov x0, #47
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
 .asciz "/emmc/usr/lib/libm26.dylib"
message:
 .ascii "XCOVER5 M26 CHILD PASS: LC_SYMTAB + named symbol binding + call47\n"
message_end:
wanted_symbol:
 .asciz "_m26_answer"
expected_layout:
 .byte 207,250,237,254,12,0,0,1,0,0,0,0,6,0,0,0
 .byte 6,0,0,0,136,1,0,0,133,0,0,0,0,0,0,0
 .byte 25,0,0,0,152,0,0,0,95,95,84,69,88,84,0,0
 .byte 0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 .byte 0,64,0,0,0,0,0,0,5,0,0,0,5,0,0,0
 .byte 1,0,0,0,0,0,0,0,95,95,116,101,120,116,0,0
 .byte 0,0,0,0,0,0,0,0,95,95,84,69,88,84,0,0
 .byte 0,0,0,0,0,0,0,0,0,4,0,0,1,0,0,0
 .byte 24,0,0,0,0,0,0,0,0,4,0,0,2,0,0,0
 .byte 0,0,0,0,0,0,0,0,0,4,0,128,0,0,0,0
 .byte 0,0,0,0,0,0,0,0,25,0,0,0,72,0,0,0
 .byte 95,95,68,65,84,65,0,0,0,0,0,0,0,0,0,0
 .byte 0,64,0,0,1,0,0,0,0,64,0,0,0,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,64,0,0,0,0,0,0
 .byte 3,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0
 .byte 25,0,0,0,72,0,0,0,95,95,76,73,78,75,69,68
 .byte 73,84,0,0,0,0,0,0,0,128,0,0,1,0,0,0
 .byte 0,64,0,0,0,0,0,0,0,128,0,0,0,0,0,0
 .byte 155,17,0,0,0,0,0,0,1,0,0,0,1,0,0,0
 .byte 0,0,0,0,0,0,0,0
