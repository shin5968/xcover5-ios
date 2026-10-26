XCover5 AUTO1 - USB test log export and ACK-gated download reset

Implemented source path:
  framebuffer serial callback -> first1MiB immutable capture
  root parent-PID1 m39-probe exit -> real wait_status + frozen CRC32 snapshot
  DWC3 EP0 vendor interface -> Windows WinUSB control transfers
  PC binary/text/receipt -> fsync + readback + CRC + same-run recheck
  exact metadata ACK -> explicit reset request -> Samsung download reset
  PC checks actual04e8:685d interface reappearance

WinUSB interface GUID: {C2CE5A15-419F-4B2B-B547-25F3CD8F78A1}
Local test USB ID:1209:0001. No production USB allocation is claimed.
OS2 descriptors ask Windows to bind its existing WinUSB driver. No custom
INF or Samsung-driver replacement is performed by the collector.

Run on Windows using Python3:
  python tools/autoloop/collect.py --reboot-download --timeout 300
Optional: --firmware-manifest path/to/verification.json
Logs default to xcover5/artifacts/autoloop-runs/<time>-<run>/.
--inventory only enumerates test interfaces and does not send commands.
Each collector handles one frozen test run. Start it before each new boot.

Protocol, little endian:
META: uint64 magic=0x31474f4c4358,run; uint32 version=1,ready,size,crc,dropped,status.
IN40 reads40bytes metadata. IN41 uses value|index<<16 as byte offset, max256bytes.
OUT42 accepts exactly the same40bytes after complete durable PC save.
OUT43 requests reset, only after a matching complete ACK.
No firmware-writing command exists. Test failure142 is still collected; it
does not become a PASS because collection succeeded.

Boot flags: xcautousb=1 enables the board USB driver;
xcautoreset=1 allows reset only after ACK + explicit PC reset request.
Without either flag that action is disabled.

First hardware gate:
This is a board bring-up implementation, not yet an end-to-end hardware PASS.
The driver reuses the Samsung loader's PHY/clock setup. It checks HSI power,
clock gates and DWC3 identity before starting. If those checks fail, it prints
STOP and does not attempt guessed clock/PHY writes. A photo of the AUTO USB
STOP line is then needed to finish PHY bring-up. No auto reset occurs.
The Samsung reset sequence is derived from the pinned Exynos3830 kernel and
the device's stock DT, but this exact new reset path still needs device test.

Coverage limits:
Only bytes passing the framebuffer serial callback are captured. Earliest
pre-serial output and other sinks are not claimed. A hard hang/early panic,
power loss, or a test that never exits cannot produce a final snapshot.
Capture overflow saves retained bytes as PARTIAL, prohibits ACK/reset, and
does not claim a complete log. No eMMC write capability was introduced.

Odin is controlled through the Computer Use skill by the active agent after
checking the exact AP and observed Odin state. This Python tool never clicks
Odin and never chooses or flashes a firmware. Idle chat wakeup is separate
from file creation; schedule a thread automation only after device validation.

Tests:
  python3 tools/autoloop/test_build.py [applied-XNU-tree]
Tests cover actual patch/header identity, concurrent capture, frozen CRC,
overflow, stale ACK, short USB reads, changing metadata, checksum failure,
disk failure, no overwrite, and saved-before-reset ordering. They are host
tests. Full XNU compile and hardware enumeration are separate checks.

Board source provenance: third_party/autoloop/ORIGIN.json.
