/* M33: one task, receive worker and send main; inline 32-byte message.
 * DATA+256 context: slots pointer +0, receive name +8. No device writes.
 * mach_task_self_ is imported DATA: dereference the bound address, do not call.
 */
.text
.globl _start
.p2align 2
_start:
anchor:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #64
 adr x23, anchor
 mov x9, #0x3800
 add x23, x23, x9
 add x19, x23, #256
 mov x24, #101
 mov x9, #0
slots:
 ldr x10, [x23, x9]
 cbz x10, failed
 add x9, x9, #8
 cmp x9, #56
 b.ne slots
 str x23, [x19]
 ldr x9, [x23]
 ldr w20, [x9]
 cbz w20, failed
 adr x1, entered
 adr x2, entered_end
 bl report
 mov x24, #102
 mov w0, w20
 mov x1, #1 /* MACH_PORT_RIGHT_RECEIVE */
 add x2, x19, #8
 ldr x9, [x23, #8]
 blr x9
 cbnz w0, failed
 ldr w21, [x19, #8]
 cbz w21, failed
 mov x24, #103
 mov w0, w20
 mov w1, w21
 mov w2, w21
 mov x3, #20 /* MACH_MSG_TYPE_MAKE_SEND */
 ldr x9, [x23, #16]
 blr x9
 cbnz w0, failed
 mov x24, #104
 add x0, sp, #32
 mov x1, #0
 adr x2, worker
 mov x3, x19
 ldr x9, [x23, #40]
 blr x9
 cbnz w0, failed
 ldr x9, [sp, #32]
 cbz x9, failed
 /* header(bits,size,remote,local,voucher,id), then two payload words */
 mov w9, #19 /* COPY_SEND */
 mov w10, #32
 stp w9, w10, [sp]
 stp w21, wzr, [sp, #8]
 mov w9, #0x4d33
 stp wzr, w9, [sp, #16]
 mov w9, #0x1234
 mov w10, #0x5678
 stp w9, w10, [sp, #24]
 mov x24, #105
 mov x0, sp
 mov x1, #0x11 /* SEND_MSG | SEND_TIMEOUT */
 mov x2, #32
 mov x3, #0
 mov x4, #0
 mov x5, #5000
 mov x6, #0
 ldr x9, [x23, #24]
 blr x9
 cbnz w0, failed
 adr x1, sent
 adr x2, sent_end
 bl report
 mov x24, #106
 ldr x0, [sp, #32]
 add x1, sp, #40
 ldr x9, [x23, #48]
 blr x9
 cbnz w0, failed
 mov x24, #107
 ldr x9, [sp, #40]
 cmp x9, x19
 b.ne failed
 mov x24, #108
 mov w0, w20
 mov w1, w21
 ldr x9, [x23, #32]
 blr x9
 cbnz w0, failed
 adr x1, passed
 adr x2, passed_end
 bl report
 mov x0, #54
 b exit_now
failed:
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
.p2align 2
worker:
 stp x29, x30, [sp, #-176]!
 stp x19, x20, [sp, #16]
 mov x29, sp
 mov x19, x0
 ldr x20, [x19]
 add x9, sp, #48
 mov x10, #8
clear:
 stp xzr, xzr, [x9], #16
 subs x10, x10, #1
 b.ne clear
 add x0, sp, #48
 mov x1, #0x102 /* RCV_MSG | RCV_TIMEOUT */
 mov x2, #0
 mov x3, #128 /* includes room for kernel trailer */
 ldr w4, [x19, #8]
 mov x5, #5000
 mov x6, #0
 ldr x9, [x20, #24]
 blr x9
 cbnz w0, worker_failed
 ldr w9, [sp, #52] /* size */
 cmp w9, #32
 b.ne worker_failed
 ldr w9, [sp, #48] /* no complex descriptors */
 tbnz w9, #31, worker_failed
 ldr w9, [sp, #60] /* local receive name */
 ldr w10, [x19, #8]
 cmp w9, w10
 b.ne worker_failed
 ldr w9, [sp, #68]
 mov w10, #0x4d33
 cmp w9, w10
 b.ne worker_failed
 ldp w9, w10, [sp, #72]
 mov w11, #0x1234
 cmp w9, w11
 b.ne worker_failed
 mov w11, #0x5678
 cmp w10, w11
 b.ne worker_failed
 mov x0, x19
 b worker_return
worker_failed:
 mov x0, #0
worker_return:
 ldp x19, x20, [sp, #16]
 ldp x29, x30, [sp], #176
 ret
entered:
 .ascii "XCOVER5 M33 CHILD: main entered, allocating Mach port\n"
entered_end:
sent:
 .ascii "XCOVER5 M33 CHILD: message sent, joining receiver\n"
sent_end:
passed:
 .ascii "XCOVER5 M33 CHILD PASS: Mach port + thread send/receive + id/body + destroy\n"
passed_end:
