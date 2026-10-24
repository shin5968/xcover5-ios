/* Only launchd's configured job executes this proof. No persistent writes. */
.text
.globl _start
.p2align 2
_start:
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 adr x0, console
 mov x1, #2
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs fail
 mov x19, x0
 mov x16, #39 /* getppid */
 svc #0x80
 cmp x0, #1
 b.ne fail
 mov x16, #20
 svc #0x80
 cmp x0, #1
 b.ls fail
 adr x1, passed
 adr x2, passed_end
 sub x2, x2, x1
 mov x0, x19
 mov x16, #4
 svc #0x80
 b.cs fail
 mov x0, #0
 mov x16, #1
 svc #0x80
fail:
 mov x0, #56
 mov x16, #1
 svc #0x80
 b fail
console: .asciz "/dev/console"
passed: .ascii "XCOVER5 M35 JOB PASS: launchd job running with parent PID1\n"
passed_end:
