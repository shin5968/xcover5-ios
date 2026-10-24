"""Run assembled M33 with mocked Mach/pthread APIs; NOT actual kernel IPC.
Worker runs at join, after send, on a separate register context/stack.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
image=Path(sys.argv[1]).read_bytes();base=0x100000000;slots=base+16384;ctx=slots+256
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6]
modes={'valid':54,'null_slot':101,'task_null':101,'allocate':102,'port_null':102,'insert':103,'create':104,'handle_null':104,'send':105,'join':106,'receive_timeout':107,'size':107,'local':107,'id':107,'body1':107,'body2':107,'complex':107,'destroy':108}
for mode,expected in modes.items():
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,65536);u.mem_write(base,image)
 u.mem_map(0x200000,0x30000);u.reg_write(UC_ARM64_REG_SP,0x20f000);u.mem_map(0x300000,65536)
 u.mem_write(slots,struct.pack('<7Q',*(0 if mode=='null_slot' and j==3 else 0x300000+16*j for j in range(7))))
 u.mem_write(0x300000,struct.pack('<I',0 if mode=='task_null' else 99))
 state={'exit':None,'out':[],'queue':None,'worker':None,'saved':None,'joined':False,'destroyed':False}
 def val(r):return u.reg_read(r)
 def result(v):u.reg_write(UC_ARM64_REG_X0,v)
 def syscall(uc,intr,data):
  n=val(UC_ARM64_REG_X16)
  if n==1:state['exit']=val(UC_ARM64_REG_X0);u.emu_stop()
  elif n==4:
   state['out'].append(bytes(u.mem_read(val(UC_ARM64_REG_X1),val(UC_ARM64_REG_X2))));result(val(UC_ARM64_REG_X2));u.reg_write(UC_ARM64_REG_NZCV,0)
  else:raise AssertionError(n)
 def hook(uc,pc,size,data):
  if pc==0x300100:
   assert val(UC_ARM64_REG_SP)==0x22f000
   for reg,v in ((UC_ARM64_REG_X19,0x1919),(UC_ARM64_REG_X20,0x2020),(UC_ARM64_REG_X29,0x2929)):assert val(reg)==v
   v=val(UC_ARM64_REG_X0);u.context_restore(state['saved']);u.mem_write(state['join_result'],struct.pack('<Q',v));state['joined']=True;result(0);u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR));return
  if not 0x300000<=pc<0x300070:return
  j=(pc-0x300000)//16;a=[val(r) for r in regs];assert val(UC_ARM64_REG_SP)%16==0
  assert j!=0, 'imported mach_task_self_ is data, must never be called'
  if j==1:
   assert a[:3]==[99,1,ctx+8];u.mem_write(a[2],struct.pack('<I',0 if mode=='port_null' else 123));result(3 if mode=='allocate' else 0)
  elif j==2:assert a[:4]==[99,123,123,20];result(17 if mode=='insert' else 0)
  elif j==3:
   assert a[5:]==[5000,0]
   if a[1]==0x11:
    assert a[2:5]==[32,0,0];msg=bytes(u.mem_read(a[0],32));assert struct.unpack('<8I',msg)==(19,32,123,0,0,0x4d33,0x1234,0x5678)
    state['queue']=msg;result(0x10000004 if mode=='send' else 0)
   else:
    assert a[1:5]==[0x102,0,128,123] and state['queue']
    if mode=='receive_timeout':result(0x10004003)
    else:
     words=[0,32,0,123,0,0x4d33,0x1234,0x5678]
     for key,idx in [('size',1),('local',3),('id',5),('body1',6),('body2',7)]:
      if mode==key:words[idx]^=1
     if mode=='complex':words[0]|=0x80000000
     u.mem_write(a[0],struct.pack('<8I',*words)+bytes(8));state['queue']=None;result(0)
  elif j==4:assert a[:2]==[99,123] and state['joined'];state['destroyed']=True;result(17 if mode=='destroy' else 0)
  elif j==5:
   assert a[1]==0 and a[3]==ctx;state['worker']=a[2];u.mem_write(a[0],struct.pack('<Q',0 if mode=='handle_null' else 1));result(11 if mode=='create' else 0)
  elif j==6:
   assert a[0]==1 and state['worker']
   if mode=='join':result(22)
   else:
    state['saved']=u.context_save();state['join_result']=a[1]
    for reg,v in ((UC_ARM64_REG_X19,0x1919),(UC_ARM64_REG_X20,0x2020),(UC_ARM64_REG_X29,0x2929),(UC_ARM64_REG_SP,0x22f000),(UC_ARM64_REG_LR,0x300100),(UC_ARM64_REG_X0,ctx),(UC_ARM64_REG_PC,state['worker'])):u.reg_write(reg,v)
    return
  u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_INTR,syscall);u.hook_add(UC_HOOK_CODE,hook);u.emu_start(base+2048,base+65532,count=10000)
 assert state['exit']==expected,(mode,state)
 assert (b'M33 CHILD PASS' in b''.join(state['out']))==(mode=='valid')
 if mode=='valid':assert state['joined'] and state['destroyed'] and state['queue'] is None
 print('PASS mocked Mach IPC:',mode)
