/* M37: fork + exec of a separate client; fresh dyld and bootstrap lookup. */
.text
.globl _start
.p2align 2
_start:
anchor:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #160
 adr x19, anchor
 mov x9, #0x3800
 add x19, x19, x9
 add x26, x19, #256
 mov x23, #0 /* unreaped child PID, parent only */
#ifdef M37_CLIENT
 mov x24, #120
 mov x16, #39
 svc #0x80
 cmp x0, #1
 b.ls failed
 mov w22, w0 /* recover server PID after exec; no inherited registers */
#else
 mov x24, #100
 mov x16, #39 /* launchd must be our parent */
 svc #0x80
 cmp x0, #1
 b.ne failed
#endif
 mov x24, #101
 mov x9, #0
slots:
 ldr x10, [x19, x9]
 cbz x10, failed
 add x9, x9, #8
 cmp x9, #104
 b.ne slots
 ldr x9, [x19]
 ldr w20, [x9]
 cbz w20, failed
#ifdef M37_CLIENT
 b child
#endif
 ldr x9, [x19, #80]
 blr x9
 mov w22, w0 /* parent's PID retained in child after fork */
 adr x1, entered
 adr x2, entered_end
 bl report
 /* Obtain launchd bootstrap port without changing the task special port. */
 mov x24, #102
 mov w0, w20
 mov x1, #4
 mov x2, x26
 ldr x9, [x19, #96]
 blr x9
 cbnz w0, failed
 mov x24, #103
 ldr w0, [x26]
 adr x1, service_name
 add x2, x26, #4
 ldr x9, [x19, #40] /* bootstrap_check_in */
 blr x9
 cbnz w0, failed
 ldr w21, [x26, #4]
 cbz w21, failed
 adr x1, checked_in
 adr x2, checked_in_end
 bl report
 mov x24, #106
 ldr x9, [x19, #64] /* libSystem fork handles its atfork state */
 blr x9
 tbnz w0, #31, failed
 cbz w0, child
 mov w23, w0
original_released:
 adr x1, parent_waiting
 adr x2, parent_waiting_end
 bl report
 mov x24, #109
 bl receive
 cbnz w0, failed
 mov x24, #110
 bl check_header
 cbnz w0, failed
 ldr w9, [sp, #20]
 mov w10, #0x4d34
 cmp w9, w10
 b.ne failed
 ldp w9, w10, [sp, #24]
 cmp w9, #0x123
 b.ne failed
 cmp w10, w23
 b.ne failed
 ldr w9, [sp] /* received remote right must be SEND_ONCE */
 and w9, w9, #255
 cmp w9, #18
 b.ne failed
 ldr w27, [sp, #8]
 cbz w27, failed
 /* Reply consumes received send-once right. */
 mov w9, #18
 mov w10, #32
 stp w9, w10, [sp]
 stp w27, wzr, [sp, #8]
 mov w9, #0x4d35
 stp wzr, w9, [sp, #16]
 mov w9, #0x456
 stp w9, w22, [sp, #24]
 mov x24, #111
 bl send
 cbnz w0, failed
 mov x25, #50
wait_peer:
 mov x24, #112
 mov w0, w23
 add x1, x26, #16
 mov x2, #1 /* WNOHANG */
 ldr x9, [x19, #72]
 blr x9
 tbnz w0, #31, failed
 cbz w0, delay
 cmp w0, w23
 b.ne failed
 mov x23, #0 /* exact child was reaped: do not kill its old PID */
 ldr w9, [x26, #16]
 mov w10, #0x3900 /* child exit57 */
 cmp w9, w10
 b.ne failed
 mov x24, #113
 mov w0, w20
 mov w1, w21
 ldr x9, [x19, #32]
 blr x9
 cbnz w0, failed
 adr x1, passed
 adr x2, passed_end
 bl report
 mov x0, #0
 b exit_now
delay:
 subs x25, x25, #1
 b.eq failed
 stp xzr, xzr, [sp, #128]
 mov w9, #34464
 movk w9, #1, lsl #16
 str w9, [sp, #136]
 mov x0, #0
 mov x1, #0
 mov x2, #0
 mov x3, #0
 add x4, sp, #128
 mov x16, #93
 svc #0x80
 b wait_peer
child:
#ifndef M37_CLIENT
 mov x23, #0
 mov x24, #128
 adr x0, client_path
 stp x0, xzr, [sp, #128] /* argv[0], NULL */
 str xzr, [sp, #144] /* empty environment */
 add x1, sp, #128
 add x2, sp, #144
 mov x16, #59 /* execve; success never returns */
 svc #0x80
 b failed
#else
 mov x23, #0
 mov x24, #121
 ldr x9, [x19]
 ldr w20, [x9] /* fork updated mach_task_self_ */
 mov w0, w20
 mov x1, #4
 add x2, x26, #20
 ldr x9, [x19, #96]
 blr x9
 cbnz w0, failed
 ldr w0, [x26, #20]
 adr x1, service_name
 add x2, x26, #12
 ldr x9, [x19, #48] /* bootstrap_look_up: no inherited service right */
 blr x9
 cbnz w0, failed
 ldr w27, [x26, #12]
 cbz w27, failed
 mov x24, #122
 mov w0, w20
 mov x1, #1
 add x2, x26, #8
 ldr x9, [x19, #8]
 blr x9
 cbnz w0, failed
 ldr w21, [x26, #8]
 cbz w21, failed
 ldr x9, [x19, #80]
 blr x9
 cmp w0, w22
 b.eq failed
 mov w10, w0
 mov w9, #0x123
 stp w9, w10, [sp, #24]
 mov w9, #0x1513 /* COPY_SEND remote, MAKE_SEND_ONCE local */
 mov w10, #32
 stp w9, w10, [sp]
 stp w27, w21, [sp, #8]
 mov w9, #0x4d34
 stp wzr, w9, [sp, #16]
 mov x24, #123
 bl send
 cbnz w0, failed
 mov x24, #124
 bl receive
 cbnz w0, failed
 mov x24, #125
 bl check_header
 cbnz w0, failed
 ldr w9, [sp, #20]
 mov w10, #0x4d35
 cmp w9, w10
 b.ne failed
 ldp w9, w10, [sp, #24]
 cmp w9, #0x456
 b.ne failed
 cmp w10, w22
 b.ne failed
 mov x24, #126
 mov w0, w20
 mov w1, w21
 ldr x9, [x19, #32]
 blr x9
 cbnz w0, failed
 mov x24, #127
 mov w0, w20
 mov w1, w27
 ldr x9, [x19, #56]
 blr x9
 cbnz w0, failed
 adr x1, peer_passed
 adr x2, peer_passed_end
 bl report
 mov x0, #57
 b exit_now
#endif
failed:
 cbz x23, fail_exit
 mov w0, w23
 mov x1, #9
 ldr x9, [x19, #88]
 blr x9
 /* Nonblocking reap; PID1 can reap an orphan if kill is not yet complete. */
 mov w0, w23
 add x1, x26, #16
 mov x2, #1
 ldr x9, [x19, #72]
 blr x9
fail_exit:
 adr x1, fail_message
 adr x2, fail_message_end
 bl report
 mov x0, x24
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
send:
 mov x0, sp
 mov x1, #0x11
 mov x2, #32
 mov x3, #0
 mov x4, #0
 mov x5, #5000
 mov x6, #0
 ldr x9, [x19, #24]
 br x9 /* tail-call keeps caller LR */
receive:
 mov x0, sp
 mov x1, #0x102
 mov x2, #0
 mov x3, #128
 mov w4, w21
 mov x5, #5000
 mov x6, #0
 ldr x9, [x19, #24]
 br x9
check_header:
 mov x0, #1
 ldr w9, [sp]
 tbnz w9, #31, header_done
 ldr w9, [sp, #4]
 cmp w9, #32
 b.ne header_done
 ldr w9, [sp, #12]
 cmp w9, w21
 b.ne header_done
 mov x0, #0
header_done:
 ret
report:
 sub x2, x2, x1
 mov x0, #1
 mov x16, #4
 svc #0x80
 ret
entered:
 .ascii "XCOVER5 M37 CHILD: checking in launchd MachServices name\n"
entered_end:
parent_waiting:
 .ascii "XCOVER5 M37 CHILD: named service ready, waiting for exec client\n"
parent_waiting_end:
peer_passed:
 .ascii "XCOVER5 M37 PEER PASS: exec client + fresh lookup + request/reply + rights cleanup\n"
peer_passed_end:
passed:
 .ascii "XCOVER5 M37 CHILD PASS: launchd check-in + exec client + request/reply + peer exit57\n"
passed_end:

service_name: .asciz "org.xcover5.m37.echo"
checked_in: .ascii "XCOVER5 M37 CHECKIN PASS: launchd supplied receive right\n"
checked_in_end:
fail_message: .ascii "XCOVER5 M37 FAIL: inspect process exit code for stage\n"
fail_message_end:

client_path: .asciz "/sbin/m37-client"
