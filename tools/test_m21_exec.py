"""Model the fork child and exec image switch using actual AArch64 text.
Syscalls are mocked: this checks control flow, not XNU process/VM behavior.
Called by test_m19_init.py when its third argument supplies probe text.
"""
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR
from unicorn.arm64_const import *

def child(parent, code, probe, mode):
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
            assert string(a[0]) == b'/emmc/sbin/m21-probe'
            argv = struct.unpack('<QQ', u.mem_read(a[1], 16))
            assert argv == (a[0], 0)
            assert bytes(u.mem_read(a[2], 8)) == bytes(8)
            if mode == 'm21_exec_error': result(8, True)
            else:
                state['exec'] = True
                u.emu_stop()
        elif n == 20:
            assert state['exec']
            result(1 if mode == 'm21_child_pid' else 17)
        elif n == 5:
            assert state['exec']
            name = string(a[0])
            if name == b'/dev/console':
                assert a[1] == 2
                result(3)
            else:
                assert name == b'/emmc/m20-proof.txt' and a[1] == 0
                result(2, True) if mode == 'm21_child_open' else result(6)
        elif n == 3:
            assert a[0] == 6 and a[2] == 128
            data = b'XCOVER5 M20 eMMC file read verified\n'
            if mode == 'm21_child_content': data = b'!'+data[1:]
            if mode == 'm21_child_short': data = data[:-1]
            if mode == 'm21_child_read': result(5, True)
            else:
                u.mem_write(a[1], data)
                result(len(data))
        elif n == 4:
            assert a[0] == 3, 'only console writes'
            output.append(bytes(u.mem_read(a[1], a[2])).decode())
            result(5, True) if mode == 'm21_child_write' else result(a[2])
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
        u.mem_write(0x300000, probe)
        u.mem_write(0x200000, bytes(0x20000))
        for reg in regs: u.reg_write(reg, 0)
        u.reg_write(UC_ARM64_REG_SP, 0x21ffe8)
        u.emu_start(0x300000, 0x310000, count=100000)
    assert state['exit'] is not None, state
    if mode == 'm21_exec_error':
        assert not state['exec'] and state['exit'] == 127
        assert 'child exec errno=00000008' in ''.join(output)
    elif mode.startswith('m21_child_'):
        assert state['exec'] and state['exit'] == 111, state
    else:
        assert state['exec'] and state['exit'] == 42, state
        assert 'M21 CHILD PASS' in ''.join(output)
    return state['exit'] << 8, output
