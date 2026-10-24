/* M31 malloc/free and one pthread with checked shared heap + join result.
 * No media writes. Pointer slots: malloc, free, create, join, self.
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
 mov x24, #101
 mov x9, #0
slots:
 ldr x10, [x23, x9]
 cbz x10, failed
 add x9, x9, #8
 cmp x9, #40
 b.ne slots
 adr x1, entered
 adr x2, entered_end
 bl report
 mov x24, #102
 mov x0, #4096
 ldr x9, [x23]
 blr x9
 cbz x0, failed
 mov x19, x0
 str x23, [x19]
 str xzr, [x19, #16]
 ldr x9, [x23, #32]
 blr x9
 mov x24, #103
 cbz x0, failed
 str x0, [x19, #8]
 mov x9, #32
 mov w10, #0x5a
fill:
 strb w10, [x19, x9]
 add x9, x9, #1
 cmp x9, #1, lsl #12
 b.ne fill
 adr x1, creating
 adr x2, creating_end
 bl report
 mov x24, #104
 stp xzr, xzr, [sp]
 mov x0, sp
 mov x1, #0
 adr x2, worker
 mov x3, x19
 ldr x9, [x23, #16]
 blr x9
 cbnz w0, failed
 mov x24, #105
 ldr x0, [sp]
 cbz x0, failed
 add x1, sp, #8
 ldr x9, [x23, #24]
 blr x9
 cbnz w0, failed
 mov x24, #106
 ldr x9, [sp, #8]
 cmp x9, x19
 b.ne failed
 ldr x9, [x19, #16]
 cmp x9, #1
 b.ne failed
 mov x24, #107
 mov x9, #32
verify:
 ldrb w10, [x19, x9]
 cmp w10, #0xa5
 b.ne failed
 add x9, x9, #1
 cmp x9, #1, lsl #12
 b.ne verify
 mov x0, x19
 ldr x9, [x23, #8]
 blr x9
 adr x1, passed
 adr x2, passed_end
 bl report
 mov x0, #52
 b exit_now
failed:
 mov x0, x24
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
/* Raw console output, preserves the caller's callee-saved registers. */
report:
 sub x2, x2, x1
 mov x0, #1
 mov x16, #4
 svc #0x80
 ret
.p2align 2
worker:
 stp x29, x30, [sp, #-32]!
 stp x19, x20, [sp, #16]
 mov x29, sp
 mov x19, x0
 ldr x20, [x19]
 adr x1, worker_msg
 adr x2, worker_msg_end
 bl report
 ldr x9, [x20, #32]
 blr x9
 cbz x0, worker_failed
 ldr x9, [x19, #8]
 cmp x0, x9
 b.eq worker_failed
 mov x9, #32
worker_verify:
 ldrb w10, [x19, x9]
 cmp w10, #0x5a
 b.ne worker_failed
 add x9, x9, #1
 cmp x9, #1, lsl #12
 b.ne worker_verify
 mov x9, #32
 mov w10, #0xa5
worker_fill:
 strb w10, [x19, x9]
 add x9, x9, #1
 cmp x9, #1, lsl #12
 b.ne worker_fill
 mov x9, #1
 str x9, [x19, #16]
 mov x0, x19
 b worker_return
worker_failed:
 mov x0, #0
worker_return:
 ldp x19, x20, [sp, #16]
 ldp x29, x30, [sp], #32
 ret
entered:
 .ascii "XCOVER5 M31 CHILD: main entered, calling malloc\n"
entered_end:
creating:
 .ascii "XCOVER5 M31 CHILD: heap initialized, calling pthread_create\n"
creating_end:
worker_msg:
 .ascii "XCOVER5 M31 THREAD: worker entered\n"
worker_msg_end:
passed:
 .ascii "XCOVER5 M31 CHILD PASS: malloc + distinct pthread + shared heap + join + free\n"
passed_end:
