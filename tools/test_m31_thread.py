"""Run real M31 instructions with mocked allocation/pthread APIs.

The scheduler runs the worker to completion at create, on a separate stack
and register context sharing memory. This checks callbacks/ABI/dataflow, not
real concurrency, Apple pthread implementation or kernel thread creation.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
image=Path(sys.argv[1]).read_bytes()
base=0x100000000; heap=0x400000; slots=base+16384
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]
modes={'valid':52,'null_slot':101,'malloc':102,'self_null':103,'create':104,
       'thread_null':105,'join':105,'same_thread':106,'worker_content':106,
       'join_result':106,'shared_content':107}
for mode,expected in modes.items():
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    u.mem_map(base,65536);u.mem_write(base,image)
    u.mem_map(0x200000,0x20000);u.reg_write(UC_ARM64_REG_SP,0x20f000)
    u.mem_map(0x300000,65536);u.mem_map(heap,65536)
    u.mem_write(heap,bytes([0xcc])*4096)
    u.mem_write(slots,struct.pack('<5Q',*(0 if mode=='null_slot' and j==2 else 0x300000+16*j for j in range(5))))
    state={'worker':False,'saved':None,'result':None,'freed':False,'joined':False,'exit':None,'out':[]}
    def val(r):return u.reg_read(r)
    def result(n):u.reg_write(UC_ARM64_REG_X0,n&((1<<64)-1))
    def syscall(uc,intr,data):
        n=val(UC_ARM64_REG_X16)
        if n==1:state['exit']=val(UC_ARM64_REG_X0);u.emu_stop()
        elif n==4:
            assert val(UC_ARM64_REG_X0)==1
            state['out'].append(bytes(u.mem_read(val(UC_ARM64_REG_X1),val(UC_ARM64_REG_X2))))
            result(val(UC_ARM64_REG_X2));u.reg_write(UC_ARM64_REG_NZCV,0)
        else:raise AssertionError(n)
    def hook(uc,pc,size,data):
        if pc==0x300100:
            assert state['worker'] and val(UC_ARM64_REG_SP)==0x21f000
            assert val(UC_ARM64_REG_X19)==0x1919 and val(UC_ARM64_REG_X20)==0x2020 and val(UC_ARM64_REG_X29)==0x2929
            state['result']=val(UC_ARM64_REG_X0)
            u.context_restore(state['saved']);state['worker']=False
            result(0);u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR));return
        if not 0x300000<=pc<0x300050:return
        j=(pc-0x300000)//16;a=[val(r) for r in regs]
        assert val(UC_ARM64_REG_SP)%16==0
        if j==0:
            assert a[0]==4096;result(0 if mode=='malloc' else heap)
        elif j==1:
            assert a[0]==heap and state['joined'] and not state['freed']
            assert bytes(u.mem_read(heap+32,4064))==bytes([0xa5])*4064
            state['freed']=True;result(0)
        elif j==2:
            assert a[1]==0 and a[3]==heap and base+2048<a[2]<base+16384
            assert bytes(u.mem_read(heap+32,4064))==bytes([0x5a])*4064
            if mode=='create':result(11)
            else:
                u.mem_write(a[0],struct.pack('<Q',0 if mode=='thread_null' else 0x2222))
                state['saved']=u.context_save();state['worker']=True
                if mode=='worker_content':u.mem_write(heap+64,b'!')
                u.reg_write(UC_ARM64_REG_SP,0x21f000)
                for reg,v in ((UC_ARM64_REG_X19,0x1919),(UC_ARM64_REG_X20,0x2020),(UC_ARM64_REG_X29,0x2929),(UC_ARM64_REG_LR,0x300100),(UC_ARM64_REG_X0,heap),(UC_ARM64_REG_PC,a[2])):u.reg_write(reg,v)
                return
        elif j==3:
            assert a[0]==0x2222 and state['result'] is not None
            if mode=='shared_content':u.mem_write(heap+100,b'!')
            u.mem_write(a[1],struct.pack('<Q',0 if mode=='join_result' else state['result']))
            state['joined']=mode!='join';result(22 if mode=='join' else 0)
        elif j==4:
            result((0x1111 if mode=='same_thread' else 0x2222) if state['worker'] else (0 if mode=='self_null' else 0x1111))
        u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR))
    u.hook_add(UC_HOOK_INTR,syscall);u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(base+2048,base+65532,count=200000)
    assert state['exit']==expected,(mode,state['exit'])
    assert state['freed']==(mode=='valid'),mode
    assert (b'M31 CHILD PASS' in b''.join(state['out']))==(mode=='valid')
    print('PASS mocked allocation/thread:',mode)
