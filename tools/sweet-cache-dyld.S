/* M29 no-import LC_MAIN executable entered by real Apple dyld.
 * Apple dyld supplies its implicit libSystem dependency; no media writes.
 * Built independently from PID 1; all data is PC-relative or on the stack.
 */
.text
.globl _start
.p2align 2
_start:
 cmp x0, #1
 b.ne failed
 ldr x9, [x1]
 cbz x9, failed
 adr x10, program_path
check_argv:
 ldrb w11, [x9], #1
 ldrb w12, [x10], #1
 cmp w11, w12
 b.ne failed
 cbnz w11, check_argv
 ldr x9, [x1, #8]
 cbnz x9, failed
 mov x9, sp
 and x9, x9, #~15
 mov sp, x9
 sub sp, sp, #128
 mov x16, #20 /* getpid: never accept PID 1 */
 svc #0x80
 b.cs failed
 cmp x0, #1
 b.le failed
 str xzr, [sp]
 mov x0, sp
 mov x16, #294 /* shared_region_check_np: success requires an installed mapping */
 svc #0x80
 b.cs failed
 ldr x9, [sp]
 cbz x9, failed
 ldr x10, [x9]
 adr x11, cache_magic
 ldr x11, [x11]
 cmp x10, x11
 b.ne failed
 adr x0, console
 mov x1, #2
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x19, x0
 adr x0, proof
 mov x1, #0 /* O_RDONLY */
 mov x2, #0
 mov x16, #5
 svc #0x80
 b.cs failed
 mov x20, x0
 mov x1, sp
 mov x2, #128
 mov x16, #3
 svc #0x80
 b.cs failed
 adr x9, expected
 adr x10, expected_end
 sub x10, x10, x9
 cmp x0, x10
 b.ne failed
 mov x11, sp
compare:
 ldrb w12, [x9], #1
 ldrb w13, [x11], #1
 cmp w12, w13
 b.ne failed
 subs x10, x10, #1
 b.ne compare
 mov x0, x20
 mov x16, #6
 svc #0x80
 mov x0, x19
 adr x1, message
 adr x2, message_end
 sub x2, x2, x1
 mov x21, x2
 mov x16, #4
 svc #0x80
 b.cs failed
 cmp x0, x21
 b.ne failed
 mov x0, #50 /* distinct from exec failure (127) or proof failure (111) */
 b exit_now
failed:
 mov x0, #111
exit_now:
 mov x16, #1
 svc #0x80
 b exit_now
console:
 .asciz "/dev/console"
proof:
 .asciz "/emmc/m20-proof.txt"
expected:
 .ascii "XCOVER5 M20 eMMC file read verified\n"
expected_end:
message:
 .ascii "XCOVER5 M29 CHILD PASS: Apple dyld main + shared cache + eMMC file read\n"
message_end:

program_path:
 .asciz "/emmc/sbin/m29-probe"

cache_magic:
 .ascii "dyld_v1 "
