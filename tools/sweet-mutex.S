/* M32: two joinable workers, 1024 checked lock/update/unlock cycles each.
 * __DATA+0x100: 128-byte opaque mutex; +0x180 counter; +0x188 slots pointer.
 * Workers preserve callback ABI. Main reads shared state only after joins.
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
 add x19, x23, #0x100
 mov x24, #101
 mov x9, #0
slots:
 ldr x10, [x23, x9]
 cbz x10, failed
 add x9, x9, #8
 cmp x9, #48
 b.ne slots
 str xzr, [x19, #128]
 str x23, [x19, #136]
 adr x1, entered
 adr x2, entered_end
 bl report
 mov x24, #102
 mov x0, x19
 mov x1, #0
 ldr x9, [x23]
 blr x9
 cbnz w0, failed
 stp xzr, xzr, [sp]
 stp xzr, xzr, [sp, #16]
 mov x22, #0
create:
 mov x24, #103
 add x24, x24, x22
 add x0, sp, x22, lsl #3
 mov x1, #0
 adr x2, worker
 mov x3, x19
 ldr x9, [x23, #32]
 blr x9
 cbnz w0, failed
 add x22, x22, #1
 cmp x22, #2
 b.ne create
 ldp x9, x10, [sp]
 mov x24, #105
 cbz x9, failed
 cbz x10, failed
 cmp x9, x10
 b.eq failed
 adr x1, joining
 adr x2, joining_end
 bl report
 mov x22, #0
join:
 mov x24, #106
 add x24, x24, x22
 ldr x0, [sp, x22, lsl #3]
 add x1, sp, #16
 add x1, x1, x22, lsl #3
 ldr x9, [x23, #40]
 blr x9
 cbnz w0, failed
 add x22, x22, #1
 cmp x22, #2
 b.ne join
 mov x24, #108
 ldp x9, x10, [sp, #16]
 cmp x9, x19
 b.ne failed
 cmp x10, x19
 b.ne failed
 mov x24, #109
 ldr x9, [x19, #128]
 cmp x9, #2048
 b.ne failed
 mov x24, #110
 mov x0, x19
 ldr x9, [x23, #24]
 blr x9
 cbnz w0, failed
 adr x1, passed
 adr x2, passed_end
 bl report
 mov x0, #53
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
 stp x29, x30, [sp, #-48]!
 stp x19, x20, [sp, #16]
 stp x21, x22, [sp, #32]
 mov x29, sp
 mov x19, x0
 ldr x20, [x19, #136]
 mov x21, #1024
worker_loop:
 mov x0, x19
 ldr x9, [x20, #8]
 blr x9
 cbnz w0, worker_failed
 ldr x9, [x19, #128]
 add x9, x9, #1
 str x9, [x19, #128]
 mov x0, x19
 ldr x9, [x20, #16]
 blr x9
 cbnz w0, worker_failed
 subs x21, x21, #1
 b.ne worker_loop
 mov x0, x19
 b worker_return
worker_failed:
 mov x0, #0
worker_return:
 ldp x21, x22, [sp, #32]
 ldp x19, x20, [sp, #16]
 ldp x29, x30, [sp], #48
 ret
entered:
 .ascii "XCOVER5 M32 CHILD: main entered, calling pthread_mutex_init\n"
entered_end:
joining:
 .ascii "XCOVER5 M32 CHILD: two workers created, joining\n"
joining_end:
passed:
 .ascii "XCOVER5 M32 CHILD PASS: two pthreads + mutex counter 2048 + joins + destroy\n"
passed_end:
