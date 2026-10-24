# M30: explicit libSystem imports

M29E passed on the device: original Apple dyld reached a no-import LC_MAIN
probe, the shared cache was present, and an eMMC file read completed. M30
adds an explicit LC_LOAD_DYLIB dependency on /usr/lib/libSystem.B.dylib.
Standard non-lazy bind opcodes resolve getpid, strlen, memcmp, read and write
into five writable pointer slots. There are no embedded Apple bytes, custom
symbol resolver, hard-coded cache addresses or lazy binder stubs.

The separate child checks imported getpid against a raw syscall, strlen
against the known proof length, unequal and equal memcmp results, imported
read of the read-only eMMC proof and imported write to inherited stdout.
The raw syscall diagnostic `M30 CHILD: entered main with five bound
libSystem slots` distinguishes main entry from a dyld failure.

Success requires both:

* `XCOVER5 M30 CHILD PASS: libSystem getpid + strlen + memcmp + read + write`
* `XCOVER5 M30 USER PASS: libSystem imports/calls + child exit 51`

The CHILD line is the data passed to write; only the parent PASS also proves
that write returned the full byte count and the child exited as expected.
Exit101..108 identify respectively: missing bound pointer, getpid mismatch,
strlen mismatch, unequal-memcmp failure, open failure, read failure/length,
equal-memcmp failure, write failure/length. Parent stages211..214 identify
fork, wait, unexpected child status, timeout. The parent retains the exact
child PID and the existing 600 x 100ms bounded wait logic. A blocking syscall
cannot be bounded by this userspace polling loop.

Local validation independently decodes the Mach-O commands, bind opcodes,
undefined/indirect symbols, segment protections and every CodeDirectory page.
Unicorn runs the real instructions with mocked imports for ten success/error
cases; it does not execute Apple libraries. The existing M29 tests and the
M30 wait/spawn error paths are checked separately. CI builds the Mach-O arm64
object and repeats structural/signature validation. Hardware success remains
pending until both M30 PASS lines are observed.

Package only boot.img, retain the root-owned userdata cache already installed
for M29E, and save outputs under xcover5/artifacts/m30. No kernel policy or
Apple runtime changes. This is a library-call milestone, not launchd,
SpringBoard or a complete iOS app environment.
