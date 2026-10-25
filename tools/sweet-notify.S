/* M38: two daemon notifications on a fresh Mach port; bounded receives. */
.text
.globl _start
.p2align 2
_start:
anchor:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #256
 adr x19, anchor
 mov x9, #0x3800
 add x19, x19, x9
 mov w20, #0 /* allocated receive port */
 mov w21, #0 /* registration exists */
 mov x24, #130
 mov x16, #39
 svc #0x80
 cmp x0, #1
 b.ne failed
 adr x1, entered
 adr x2, entered_end
 bl report
 str wzr, [sp, #160]
 str wzr, [sp, #164]
 adr x0, name
 add x1, sp, #160
 mov x2, #0 /* no NOTIFY_REUSE */
 add x3, sp, #164
 ldr x9, [x19]
 blr x9
 mov x24, #131
 cbnz w0, failed
 mov w21, #1
 ldr w20, [sp, #160]
 cbz w20, failed
 mov w22, #2
loop:
 adr x0, name
 ldr x9, [x19, #8]
 blr x9
 mov x24, #132
 cbnz w0, failed
 mov x0, sp
 mov x1, #0x102 /* MACH_RCV_MSG | MACH_RCV_TIMEOUT */
 mov x2, #0
 mov x3, #128
 mov w4, w20
 mov x5, #5000
 mov x6, #0
 ldr x9, [x19, #24]
 blr x9
 mov x24, #133
 cbnz w0, failed
 mov x24, #134
 ldr w9, [sp]
 tbnz w9, #31, failed
 ldr w9, [sp, #4]
 cmp w9, #24
 b.ne failed
 ldr w9, [sp, #12]
 cmp w9, w20
 b.ne failed
 ldr w9, [sp, #20]
 ldr w10, [sp, #164]
 cmp w9, w10
 b.ne failed
 subs w22, w22, #1
 b.ne loop
 ldr w0, [sp, #164]
 ldr x9, [x19, #16]
 blr x9
 mov x24, #135
 cbnz w0, failed
 mov w21, #0
 ldr w0, [sp, #164]
 ldr x9, [x19, #32]
 blr x9
 mov x24, #136
 cbnz w0, failed
 mov w20, #0
 adr x1, passed
 adr x2, passed_end
 bl report
 mov x0, #58
 b exit_now
failed:
 cbz w21, no_cancel
 ldr w0, [sp, #164]
 ldr x9, [x19, #16]
 blr x9
no_cancel:
 /* notify_cancel releases its library-owned port. */
 adr x1, failure
 adr x2, failure_end
 bl report
 mov x0, x24
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
report:
 sub x2, x2, x1
 mov x0, #1
 mov x16, #4
 svc #0x80
 ret
entered: .ascii "XCOVER5 M38: registering with Apple notifyd\n"
entered_end:
passed: .ascii "XCOVER5 M38 PASS: notify register + two posts/receives + token + cancel + registration cleanup\n"
passed_end:
failure: .ascii "XCOVER5 M38 FAIL: inspect exit130-136 for stage\n"
failure_end:
name: .asciz "org.xcover5.m38.notification"

