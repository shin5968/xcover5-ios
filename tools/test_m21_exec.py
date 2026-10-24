"""Model the fork child and exec image switch using actual AArch64 text.
Syscalls are mocked: this checks control flow, not XNU process/VM behavior.
Called by test_m19_init.py when its third argument supplies probe text.
"""
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR
from unicorn.arm64_const import *

def child(parent, code, probe, mode, dynamic=None, mapped=None, cow=None, library=None):
    label = 'M25' if library else 'M24' if cow else ('M23' if mapped else ('M22' if dynamic else 'M21'))
    prefix = label.lower()
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    for base, size in [(0x100000, 0x10000), (0x200000, 0x20000), (0x300000, 0x10000)]:
        u.mem_map(base, size)
    u.mem_write(0x100000, code)
    u.mem_write(0x200000, bytes(parent.mem_read(0x200000, 0x20000)))
    regs = [getattr(__import__('unicorn.arm64_const', fromlist=['']), f'UC_ARM64_REG_X{i}') for i in range(31)]
    for reg in regs + [UC_ARM64_REG_SP, UC_ARM64_REG_PC, UC_ARM64_REG_NZCV]:
        u.reg_write(reg, parent.reg_read(reg))
    u.reg_write(UC_ARM64_REG_X0, 17)  # raw Darwin fork child result is not zero
    u.reg_write(UC_ARM64_REG_X1, 1)
    u.reg_write(UC_ARM64_REG_NZCV, u.reg_read(UC_ARM64_REG_NZCV) & ~(1 << 29))
    output, state = [], {'exec': False, 'exit': None}
    def string(p):
        return bytes(u.mem_read(p, 80)).split(b'\0')[0]
    def result(v, error=False):
        u.reg_write(UC_ARM64_REG_X0, v)
        flags = u.reg_read(UC_ARM64_REG_NZCV) & ~(1 << 29)
        u.reg_write(UC_ARM64_REG_NZCV, flags | ((1 << 29) if error else 0))
    def syscall(uc, intr, _):
        n = u.reg_read(UC_ARM64_REG_X16)
        a = [u.reg_read(r) for r in regs[:4]]
        if n == 59:
            assert not state['exec']
            assert string(a[0]) == f'/emmc/sbin/{prefix}-probe'.encode()
            argv = struct.unpack('<QQ', u.mem_read(a[1], 16))
            assert argv == (a[0], 0)
            assert bytes(u.mem_read(a[2], 8)) == bytes(8)
            if mode == prefix+'_exec_error': result(8, True)
            else:
                state['exec'] = True
                u.emu_stop()
        elif n == 20:
            assert state['exec']
            result(1 if mode == prefix+'_child_pid' else 17)
        elif n == 5:
            assert state['exec']
            name = string(a[0])
            if name == b'/dev/console':
                assert a[1] == 2
                result(3)
            else:
                assert name == (b'/emmc/usr/lib/libm25.dylib' if library else b'/emmc/usr/lib/m23-code' if (mapped or cow) else b'/emmc/m20-proof.txt') and a[1] == 0
                result(2, True) if mode == prefix+'_child_open' else result(6)
        elif n == 153 and library:
            count = state.get('pread', 0)
            state['pread'] = count + 1
            assert a == [6, u.reg_read(UC_ARM64_REG_SP)+(512 if count else 0), 8 if count else 512, 16384 if count else 0]
            data = bytearray(library[1][a[3]:a[3]+a[2]])
            if mode == 'm25_child_layout' and not count: data[72] ^= 1
            if mode == 'm25_child_original' and count: data[0] ^= 1
            u.mem_write(a[1], bytes(data))
            result(a[2]-1 if mode == 'm25_child_short' else a[2])
        elif n == 197 and library:
            count = state.get('maps', 0)
            state['maps'] = count + 1
            args = [u.reg_read(r) for r in regs[:6]]
            assert args == [0, 16384, 3 if count else 5, 2, 6, 16384 if count else 0], args
            if mode == ('m25_child_map_data' if count else 'm25_child_mmap'): result(13, True)
            else:
                addr = 0x680000 if count else 0x600000 # deliberately non-contiguous
                data = bytearray(library[1][count*16384:(count+1)*16384])
                if mode == 'm25_child_pointer' and count: data[0] ^= 1
                if mode == 'm25_child_return' and not count: data[1024:1028] = struct.pack('<I',0x528005a0)
                u.mem_map(addr, 16384)
                u.mem_write(addr, bytes(data))
                u.mem_protect(addr, 16384, args[2])
                result(addr)
        elif n == 74 and library:
            assert a[:3] == [0x680000, 16384, 1]
            assert struct.unpack('<Q',u.mem_read(0x680000,8))[0] == 0x600400
            if mode == 'm25_child_protect': result(13, True)
            else:
                u.mem_protect(a[0],a[1],a[2])
                result(0)
        elif n == 73 and library:
            count = state.get('unmaps',0)
            state['unmaps'] = count+1
            assert a[:2] == [0x680000 if count else 0x600000, 16384]
            if mode == 'm25_child_munmap': result(22,True)
            else:
                u.mem_unmap(a[0],a[1])
                result(0)
        elif n == 153 and cow:
            count = state.get('pread', 0)
            state['pread'] = count + 1
            assert a == [6, u.reg_read(UC_ARM64_REG_SP) + (32 if count else 0), 32, 0]
            data = cow[1][:32]
            if mode == 'm24_child_original' and count: data = b'!' + data[1:]
            u.mem_write(a[1], data)
            result(31 if mode == 'm24_child_short' else 32)
        elif n == 197 and cow:
            count = state.get('maps', 0)
            state['maps'] = count + 1
            args = [u.reg_read(r) for r in regs[:6]]
            prot = 1 if count else 3
            assert args == [0, 16384, prot, 2, 6, 0], args
            if mode == ('m24_child_map_ro' if count else 'm24_child_mmap'):
                result(13, True)
            else:
                addr = 0x600000 + count * 16384
                data = bytearray(cow[1][:16384])
                if mode == 'm24_child_content': data[0] ^= 1
                u.mem_map(addr, 16384)
                u.mem_write(addr, bytes(data))
                u.mem_protect(addr, 16384, prot)
                result(addr)
        elif n == 74 and cow:
            assert a[:3] == [0x600000, 16384, 1]
            assert bytes(u.mem_read(0x600000, 8)) != cow[1][:8]
            assert bytes(u.mem_read(0x604000, 32)) == cow[1][:32]
            if mode == 'm24_child_protect': result(13, True)
            else:
                u.mem_protect(a[0], a[1], a[2])
                result(0)
        elif n == 73 and cow:
            count = state.get('unmaps', 0)
            state['unmaps'] = count + 1
            assert a[:2] == [0x600000 + count * 16384, 16384]
            if mode == 'm24_child_munmap': result(22, True)
            else:
                u.mem_unmap(a[0], a[1])
                result(0)
        elif n == 153 and mapped:
            assert a == [6, u.reg_read(UC_ARM64_REG_SP), 32, 0]
            u.mem_write(a[1], mapped[1][:32])
            result(31 if mode == 'm23_child_short' else 32)
        elif n == 197 and mapped:
            args = [u.reg_read(r) for r in regs[:6]]
            assert args == [0, 16384, 5, 2, 6, 0], args
            if mode == 'm23_child_mmap': result(13, True)
            else:
                data = bytearray(mapped[1][:16384])
                if mode == 'm23_child_content': data[0] ^= 1
                if mode == 'm23_child_return': data[1024:1028] = struct.pack('<I', 0x52800560) # mov w0,43
                u.mem_map(0x600000, 16384)
                u.mem_write(0x600000, bytes(data))
                u.mem_protect(0x600000, 16384, 5)
                result(0x600000)
        elif n == 73 and mapped:
            assert a[:2] == [0x600000, 16384]
            if mode == 'm23_child_munmap': result(22, True)
            else:
                u.mem_unmap(a[0], a[1])
                result(0)
        elif n == 3:
            assert a[0] == 6 and a[2] == 128
            data = b'XCOVER5 M20 eMMC file read verified\n'
            if mode == prefix+'_child_content': data = b'!'+data[1:]
            if mode == prefix+'_child_short': data = data[:-1]
            if mode == prefix+'_child_read': result(5, True)
            else:
                u.mem_write(a[1], data)
                result(len(data))
        elif n == 4:
            assert a[0] == 3, 'only console writes'
            output.append(bytes(u.mem_read(a[1], a[2])).decode())
            result(5, True) if mode == prefix+'_child_write' else result(a[2])
        elif n == 6: result(0)
        elif n == 1:
            state['exit'] = a[0]
            u.emu_stop()
        else: raise AssertionError(('unexpected child syscall', n))
    u.hook_add(UC_HOOK_INTR, syscall)
    u.emu_start(u.reg_read(UC_ARM64_REG_PC), 0x110000, count=100000)
    if state['exec']:
        # Simulate exec: only the new image and a fresh, deliberately unaligned
        # initial stack survive; register inheritance cannot make the probe pass.
        u.mem_write(0x100000, bytes(len(code)))
        u.mem_write(0x200000, bytes(0x20000))
        for reg in regs: u.reg_write(reg, 0)
        if dynamic:
            from test_m22_loader import prepare
            pc = prepare(u, *dynamic)
            u.emu_start(pc, 0x600000, count=100000)
        else:
            u.mem_write(0x300000, library[0] if library else cow[0] if cow else (mapped[0] if mapped else probe))
            u.reg_write(UC_ARM64_REG_SP, 0x21ffe8)
            u.emu_start(0x300000, 0x310000, count=100000)
    assert state['exit'] is not None, state
    if mode == prefix+'_exec_error':
        assert not state['exec'] and state['exit'] == 127
        assert 'child exec errno=00000008' in ''.join(output)
    elif mode.startswith(prefix+'_child_'):
        assert state['exec'] and state['exit'] in (range(141, 153) if library else range(121, 131) if cow else (range(101, 109) if mapped else (111, 112))), state
    else:
        assert state['exec'] and state['exit'] == (46 if library else 45 if cow else (44 if mapped else (43 if dynamic else 42))), state
        assert label+' CHILD PASS' in ''.join(output)
        if dynamic: assert 'M22 LOADER PASS' in ''.join(output)
    return state['exit'] << 8, output
