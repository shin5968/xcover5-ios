# XCover5 HackiOS integration (M74)

Reference: `oosexgang/hackios-xnu-kernel` commit
`a3384e031eb1e605cf37adaefc19991f04f6274b`.
Target kernel: XNU 8796.141.3; upstream kernel patch targets 8796.121.2.

The existing Samsung port is the destination. Qualcomm hardware addresses,
firmware and loader callbacks are not a substitute for Exynos drivers.

| Area | Integrated behavior | Validation / remaining boundary |
| --- | --- | --- |
| launchd and process startup | Existing Apple launchd/xpcproxy/notifyd/cfprefsd and 21 UI/system jobs retained. M72 adds configd and fontservicesd using HackiOS's demand-start policy. | Two new jobs start through Mach service requests, with 30-second restart throttling; no autonomous periodic jobs. |
| Sandbox / AMFI | Existing M62 MiniMAC, MiniAMFI and entitlement compatibility remain active. Latest upstream MiniAMFI/entitlement files introduce no new changes; MiniMAC differences are comments. | Development port policy, not stock iPhone security. No separate new security bypass is needed for M72. |
| AppleKeyStore | M70 service discovery, event interest registration and fixed volatile no-passcode initial queries retained. | No SEP, persistent bags, secure key wrapping, real passcode or biometric support. Upstream reversible test key wrapping is not represented as encryption. |
| Display | M68 native IOMobileFramebuffer request ABI, CPU layer composition, timer notification, actual Samsung copy/readback and restore retained. | Samsung panel geometry/mapping preserved. No Qualcomm GPU or synthetic GPU capability. M72 does not prove lockscreen rendering. |
| M73 display observation | Root-only actual frame/layer/RGB/error counters and guarded saved-console recovery; one virtual HID wake tap after recovered blank output. | M72 video shows native display blanking before submission; actual payload/result and subsequent CPU state are unknown. Recovery requires the last successful black frame to age at least2s. Physical Samsung input and lockscreen rendering remain unverified. |
| IOSurface | Upstream plane-dimension and 64-bit plane-byte checks plus wrapped-allocation recheck added; existing create-result lifetime fix retained. | Existing BGRA-only admission and 8 MiB surface / 32 MiB total allocation limits remain. Multi-plane, external wrapped buffers and Metal are not enabled. |
| Input | HackiOS 24-byte event ABI and 512-record queue ported. `/dev/hakios-touch` and the old injection's `/dev/redwood-touch` use the same queue. | Single reader, root-only writes (0644), nonblocking read, interrupted waits, copy-error requeue and wrap/overflow tested. Physical Samsung touch/button backend remains required. No automatic unlock gestures. |
| Network discovery | IONetworkStack / IONetworkStackUserClient registered under IOResources as expected by configd's InterfaceNamer. | Opens the standard service; refuses requests to name nonexistent IOKit interfaces. No NIC, IP address, radio, DHCP or connectivity is fabricated. |
| APFS | HackiOS read-only VFS/vnode driver, metadata reader, zlib/libdeflate and zbitmap support compiled and registered. | Existing HFS root/cache boot stays active. APFS is not mounted as the boot root. No encryption, snapshot boot, Fusion or disk writes. Default metadata cache 512 blocks, 256 KiB read buffer, two retained buffers. |
| RAMFS | M74 adds an owned pre-launchd helper to mount registered RAMFS on `/private/var`, restore133 existing fresh-var records, and test1MiB mobile write/readback before original launchd. | Native mount, restore and probe require hardware validation; failure stops handoff and keeps PID1 alive. Data resets every boot. File-data quota is min(RAM/4,32MiB) per mount; metadata additional. Existing read-only M72 HFS cache retained. |
| UI identity | A local-only D22AP metadata merge adds `/product`, including the model product-id; scale2/sRGB matches native software display profile. | Owned fixtures verify that Samsung CPU, RAM, MMIO and other hardware data are preserved. Apple hardware nodes, serial/ECID/MAC, camera/haptics and syscfg placeholders are excluded. |
| Resources | M71's 2692 original framework Info.plists retained. M72 adds 39 local original files (1,294,496 bytes), including configd/fontservicesd and common SystemConfiguration plugin resources. | Raw HFS owner/mode/file comparison and independent extraction. Apple bytes are injected locally, never included in the new public source commits or CI inputs. The extended image adds every file of the stock Fonts directory (256), plus 186 UI bundle files on the read-only cache: 442 files / 403,413,560 bytes. 89 root links expose the complete Fonts directory and selected SpringBoard/UIKit/CoreUI resources. Existing framework directory identities remain in place; media services and the complete stock root are not claimed. |
| M73 current CoreDuet model | Missing `_DKDataModel.momd` current version35 restored: `.mom`, `.omo` and original `VersionInfo.plist`,190863bytes. | Exact APFS/independent7Zip/final-HFS bytes verified locally. Addresses and resource lookup inferred from chronod's NSURL nil-path exception; actual exception resolution needs hardware. Historical migration model versions are not staged. |
| User-space injection | Existing BackBoard/SpringBoard software-rendering hooks retained. | Latest upstream injection removes workarounds that this GPU-less port still needs; its modem/GPU/camera hooks cannot simply replace the current library. |

New portable source is pinned in `third_party/hackios-portable/ORIGIN.json`.
The immutable upstream files and their licenses are retained; Samsung adaptations
are a separate strict patch, `xnu/patches/0095-xcover5-hackios-portable.patch`.
CI checks the hashes of the actual staged/applied source and the linked service
markers, and runs the actual input/network/parser bodies with owned mocks.

The final local package keeps the validated 255 MiB RAM range, stock Samsung DTB,
shim, command line and M66 cache format. A boot-only archive requires the matched M72 cache. The combined archive explicitly named
`ERASE_USERDATA_CACHE` contains boot.img and userdata.img.lz4, replacing the userdata cache.
Nothing flashes the device automatically.

M73 is a boot-only update requiring the already installed M72 cache. Its archive
has only `boot.img`; it does not replace userdata. M72 video and M73 package
provenance/limitations are recorded in `M73_DISPLAY_RECOVERY_STATUS.txt` and
`M73_M72_VIDEO_REVIEW.json`. Actual lockscreen rendering remains pending.

M73 hardware subsequently confirmed actual console recovery and CoreDuet model
lookup, but showed runtime root available space0, chronod ENOSPC and SpringBoard
SQLite-journal failure. M74 therefore separates writable var from the24MiB boot
root. M74's boot-only package also reuses the installed M72 cache. See
`M74_WRITABLE_VAR_STATUS.txt` and `M74_M73_VIDEO_REVIEW.json`; actual lockscreen
rendering and physical Samsung input remain unestablished.

The next storage migration is a read-only complete stock resource/root view using
the new APFS reader, with writable var and selected job overlays. The 24 MiB boot root now exposes fonts and selected UI resources from the existing
3 GiB read-only HFS cache format. Moving the complete stock root and the rest of its
services to APFS still requires its own verified Samsung block-device layout; APFS
boot is not silently enabled by registering the filesystem.
