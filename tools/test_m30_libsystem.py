"""Independent Mach-O/bind decoder and signature checks; no Apple execution.
Usage: test_m30_libsystem.py MACHO [--emulate]. Emulation mocks imported calls.
"""
import hashlib
import struct
import sys
from pathlib import Path

b = Path(sys.argv[1]).read_bytes()
commands = {}; segments = []; off = 32
for _ in range(struct.unpack_from('<I', b, 16)[0]):
    cmd, size = struct.unpack_from('<II', b, off)
    assert size >= 8 and size % 8 == 0
    record = b[off:off+size]
    if cmd == 0x19: segments.append(record)
    else: assert cmd not in commands; commands[cmd] = record
    off += size
assert off == 32+struct.unpack_from('<I', b, 20)[0] and off <= 2048
assert [s[8:24].rstrip(b'\0') for s in segments] == [b'__PAGEZERO', b'__TEXT', b'__DATA', b'__LINKEDIT']
assert struct.unpack_from('<I', b, 24)[0] & 0x80  # two-level namespace
assert struct.unpack_from('<Q', commands[0x80000028], 8)[0] == 2048
assert struct.unpack_from('<I', commands[0x32], 8)[0] == 2
assert commands[0xc][24:].rstrip(b'\0') == b'/usr/lib/libSystem.B.dylib'
base = 0x100000000
for seg, vm, fo, prot in zip(segments[1:], (base,base+16384,base+32768), (0,16384,32768), (5,3,1)):
    assert struct.unpack_from('<Q', seg, 24)[0] == vm
    assert struct.unpack_from('<Q', seg, 40)[0] == fo
    assert struct.unpack_from('<II', seg, 56) == (prot,prot)
assert b[16384:32768] == bytes(16384)
assert struct.unpack_from('<III', segments[2], 72+64) == (6,0,0)
info = struct.unpack_from('<10I', commands[0x80000022], 8)
assert info[:2] == (0,0) and info[4:] == (0,)*6
stream = b[info[2]:info[2]+info[3]]
# Interpret the supported bind opcode subset independently of the builder.
i = 0; ordinal = typ = segment = offset = None; symbol = None; binds = []
while i < len(stream):
    op = stream[i]; i += 1; kind = op & 0xf0; imm = op & 15
    if op == 0: assert i == len(stream); break
    if kind == 0x10: ordinal = imm
    elif kind == 0x50: typ = imm
    elif kind == 0x70:
        segment = imm; offset = 0; shift = 0
        while True:
            v = stream[i]; i += 1; offset |= (v&127)<<shift
            if not v&128: break
            shift += 7
    elif kind == 0x40:
        assert imm == 0
        end = stream.index(0,i); symbol = stream[i:end]; i = end+1
    elif op == 0x90:
        binds.append((ordinal,typ,segment,offset,symbol)); offset += 8
    else: raise AssertionError(hex(op))
names = ([b'_malloc',b'_free',b'_pthread_create',b'_pthread_join',b'_pthread_self'] if '--thread' in sys.argv else [b'_getpid',b'_strlen',b'_memcmp',b'_read',b'_write'])
if '--mutex' in sys.argv: names=[b'_pthread_mutex_init',b'_pthread_mutex_lock',b'_pthread_mutex_unlock',b'_pthread_mutex_destroy',b'_pthread_create',b'_pthread_join']
if '--ipc' in sys.argv: names=[b'_mach_task_self_',b'_mach_port_allocate',b'_mach_port_insert_right',b'_mach_msg',b'_mach_port_destroy',b'_pthread_create',b'_pthread_join']
if '--process-ipc' in sys.argv: names=list((b'_mach_task_self_',b'_mach_port_allocate',b'_mach_port_insert_right',b'_mach_msg',b'_mach_port_destroy',b'_task_get_special_port',b'_task_set_special_port',b'_mach_port_deallocate',b'_fork',b'_waitpid',b'_getpid',b'_kill'))
assert binds == [(1,1,2,8*j,n) for j,n in enumerate(names)]
so, ns, st, ss = struct.unpack_from('<4I', commands[2], 8)
assert ns == len(names)
for j,name in enumerate(names):
    sx,ty,se,de,val = struct.unpack_from('<IBBHQ', b, so+16*j)
    assert (ty,se,de,val) == (1,0,0x100,0)
    assert b[st+sx:st+ss].split(b'\0')[0] == name
dysym = struct.unpack_from('<18I', commands[0xb], 8)
assert dysym[:6] == (0,0,0,0,0,len(names))
ind, count = dysym[12:14]
assert count == len(names) and struct.unpack_from('<%dI' % count, b, ind) == tuple(range(count))
sigoff, sigsize = struct.unpack_from('<II', commands[0x1d], 8)
linkoff,linksize = struct.unpack_from('<QQ', segments[3], 40)
assert linkoff <= info[2] < so < st < ind < sigoff
assert sigoff+sigsize == len(b) == linkoff+linksize
sig = b[sigoff:]; assert struct.unpack_from('>3I',sig) == (0xfade0cc0,len(sig),1)
cd = sig[struct.unpack_from('>I',sig,16)[0]:]
hashoff,_,special,slots,limit = struct.unpack_from('>5I',cd,16)
assert special == 0 and limit == sigoff and slots == (limit+4095)//4096
for j in range(slots):
    assert cd[hashoff+32*j:hashoff+32*(j+1)] == hashlib.sha256(b[j*4096:min(limit,(j+1)*4096)]).digest()
print('PASS: load commands, RW data/RX text, ordinal-1 imports, bind stream, symbol/indirect tables, every signature page')

if '--emulate' in sys.argv:
    from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_INTR,UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X16,UC_ARM64_REG_SP,UC_ARM64_REG_LR,UC_ARM64_REG_PC,UC_ARM64_REG_NZCV
    regs = [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]
    proof = b'XCOVER5 M20 eMMC file read verified\n'
    for mode in ('valid','null_slot','pid','strlen','memcmp_unequal','open','read_short','read_error','content','write_short'):
        u = Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        u.mem_map(base,65536); u.mem_write(base,b)
        u.mem_map(0x200000,65536); u.reg_write(UC_ARM64_REG_SP,0x20f000)
        u.mem_map(0x300000,65536)
        u.mem_write(base+16384,struct.pack('<5Q',*(0 if mode=='null_slot' and j==2 else 0x300000+16*j for j in range(5))))
        outputs=[]; calls=[]; exited=[]
        def cstring(p): return bytes(u.mem_read(p,128)).split(b'\0')[0]
        def ret(v,error=False):
            u.reg_write(UC_ARM64_REG_X0,v&((1<<64)-1))
            u.reg_write(UC_ARM64_REG_NZCV,(1<<29) if error else 0)
        def syscall(uc,intr,data):
            a=[u.reg_read(r) for r in regs]; n=u.reg_read(UC_ARM64_REG_X16)
            if n==1: exited.append(a[0]); u.emu_stop()
            elif n==20: ret(9)
            elif n==5:
                assert cstring(a[0])==b'/emmc/m20-proof.txt' and a[1:]==[0,0]
                ret(2,True) if mode=='open' else ret(6)
            elif n==6: assert a[0]==6; ret(0)
            elif n==4: outputs.append(bytes(u.mem_read(a[1],a[2]))); ret(a[2])
            else: raise AssertionError(n)
        def imported(uc,pc,size,data):
            if not 0x300000<=pc<0x300050:return
            j=(pc-0x300000)//16;calls.append(names[j]); a=[u.reg_read(r) for r in regs]
            if j==0: ret(8 if mode=='pid' else 9)
            elif j==1: ret(len(cstring(a[0]))+(mode=='strlen'))
            elif j==2:
                left=bytes(u.mem_read(a[0],a[2]));right=bytes(u.mem_read(a[1],a[2]))
                ret(0 if mode=='memcmp_unequal' else (left>right)-(left<right))
            elif j==3:
                assert a[0]==6 and a[2]==128
                u.mem_write(a[1],(b'!'+proof[1:]) if mode=='content' else proof)
                ret(-1 if mode=='read_error' else len(proof)-(mode=='read_short'))
            elif j==4:
                assert a[0]==1
                outputs.append(bytes(u.mem_read(a[1],a[2])));ret(a[2]-(mode=='write_short'))
            u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
        u.hook_add(UC_HOOK_INTR,syscall);u.hook_add(UC_HOOK_CODE,imported)
        u.emu_start(base+2048,base+65532,count=100000)
        expected={'valid':51,'null_slot':101,'pid':102,'strlen':103,'memcmp_unequal':104,'open':105,'read_short':106,'read_error':106,'content':107,'write_short':108}[mode]
        assert exited==[expected],(mode,exited)
        if mode=='valid':assert set(calls)==set(names) and b'M30 CHILD PASS' in b''.join(outputs)
        print('PASS mocked imports:',mode)
