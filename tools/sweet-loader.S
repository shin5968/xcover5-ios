/* M22 diagnostic MH_DYLINKER. No imports, relocations or dylib binding.
 * XNU puts the main Mach-O header pointer ahead of argc on the entry stack.
 * Validate this restricted image, locate LC_MAIN and hand off at its runtime
 * address, independent of the random slide chosen for either image.
 */
.text
.globl _start
.p2align 2
_start:
 mov x21, sp
 ldr x20, [x21]
 and x9, x21, #~15
 mov sp, x9
 cbz x20, bad
 ldr w9, [x20]
 mov w10, #0xfacf
 movk w10, #0xfeed, lsl #16
 cmp w9, w10
 b.ne bad
 ldr w9, [x20, #4]
 mov w10, #0xc
 movk w10, #0x100, lsl #16
 cmp w9, w10
 b.ne bad
 ldr w9, [x20, #12]
 cmp w9, #2
 b.ne bad
 ldr w11, [x20, #16]
 cbz w11, bad
 cmp w11, #16
 b.hi bad
 ldr w12, [x20, #20]
 cmp w12, #992
 b.hi bad
 add x13, x20, #32
 mov x23, #0
commands:
 cmp w12, #8
 b.lo bad
 ldp w9, w10, [x13]
 cmp w10, #8
 b.lo bad
 tst w10, #7
 b.ne bad
 cmp w10, w12
 b.hi bad
 mov w14, #0x28
 movk w14, #0x8000, lsl #16
 cmp w9, w14
 b.ne next
 cbnz x23, bad
 cmp w10, #24
 b.ne bad
 ldr x23, [x13, #8]
 cmp x23, #1024
 b.lo bad
 cmp x23, #4, lsl #12
 b.hs bad
 tst x23, #3
 b.ne bad
next:
 sub w12, w12, w10
 add x13, x13, x10
 subs w11, w11, #1
 b.ne commands
 cbnz w12, bad
 cbz x23, bad
 ldr x9, [x21, #8]
 cmp x9, #1
 b.ne bad
 ldr x9, [x21, #16]
 cbz x9, bad
 ldp x9, x10, [x21, #24] /* argv terminator + empty environment */
 orr x9, x9, x10
 cbnz x9, bad
 adr x0, console
 mov x1, #2
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs bad
 mov x19, x0
 adr x1, message
 adr x2, message_end
 sub x2, x2, x1
 mov x22, x2
 mov x16, #4
 svc #0x80
 b.cs bad
 cmp x0, x22
 b.ne bad
 mov x0, x19
 mov x16, #6
 svc #0x80
 /* main(argc, argv, envp, apple); x15 is a private test handshake. */
 mov x0, #1
 add x1, x21, #16
 add x2, x21, #32
 add x3, x21, #40
 mov w15, #0x3232
 movk w15, #0x4d, lsl #16
 add x23, x20, x23
 br x23
bad:
 mov x0, #112
 mov x16, #1
 svc #0x80
 b bad
console:
 .asciz "/dev/console"
message:
 .ascii "XCOVER5 M22 LOADER PASS: kernel handoff + LC_MAIN\n"
message_end:
