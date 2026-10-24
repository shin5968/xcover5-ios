"""M32 instruction tests with mocked pthread/mutex calls, NOT real concurrency.
Workers run serially on separate stacks/register contexts sharing DATA.
Checks lock ownership on every counter write and callback callee-save ABI.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR,UC_HOOK_MEM_WRITE
from unicorn.arm64_const import *
image=Path(sys.argv[1]).read_bytes();base=0x100000000;slots=base+16384;mutex=slots+256
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]
modes={'valid':53,'null_slot':101,'init':102,'create1':103,'create2':104,
 'same_handle':105,'null_handle':105,'join1':106,'join2':107,'lock':108,
 'unlock':108,'result':108,'counter':109,'destroy':110}
for mode,expected in modes.items():
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,65536);u.mem_write(base,image)
 u.mem_map(0x200000,0x30000);u.reg_write(UC_ARM64_REG_SP,0x20f000);u.mem_map(0x300000,65536)
 u.mem_write(slots,struct.pack('<6Q',*(0 if mode=='null_slot' and j==2 else 0x300000+16*j for j in range(6))))
 state={'worker':0,'saved':None,'results':{},'creates':0,'joins':0,'held':False,'locks':0,'unlocks':0,'writes':0,'init':False,'destroy':False,'exit':None,'out':[]}
 def val(r):return u.reg_read(r)
 def result(v):u.reg_write(UC_ARM64_REG_X0,v)
 def syscall(uc,intr,data):
  n=val(UC_ARM64_REG_X16)
  if n==1:state['exit']=val(UC_ARM64_REG_X0);u.emu_stop()
  elif n==4:
   state['out'].append(bytes(u.mem_read(val(UC_ARM64_REG_X1),val(UC_ARM64_REG_X2))))
   result(val(UC_ARM64_REG_X2));u.reg_write(UC_ARM64_REG_NZCV,0)
  else:raise AssertionError(n)
 def write(uc,access,address,size,value,data):
  if address==mutex+128 and state['worker']:
   assert state['held'] and size==8
   assert value==struct.unpack('<Q',u.mem_read(address,8))[0]+1
   state['writes']+=1
 def hook(uc,pc,size,data):
  if pc==0x300100:
   worker=state['worker'];assert worker and val(UC_ARM64_REG_SP)==0x210000+worker*0x8000
   for reg,v in ((UC_ARM64_REG_X19,0x1919),(UC_ARM64_REG_X20,0x2020),(UC_ARM64_REG_X21,0x2121),(UC_ARM64_REG_X22,0x2222),(UC_ARM64_REG_X29,0x2929)):assert val(reg)==v
   state['results'][worker]=val(UC_ARM64_REG_X0);u.context_restore(state['saved']);state['worker']=0
   result(0);u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR));return
  if not 0x300000<=pc<0x300060:return
  j=(pc-0x300000)//16;a=[val(r) for r in regs];assert val(UC_ARM64_REG_SP)%16==0
  if j==0:
   assert a[:2]==[mutex,0];state['init']=mode!='init';result(22 if mode=='init' else 0)
  elif j==1:
   assert a[0]==mutex and state['init'] and state['worker'] and not state['held']
   state['locks']+=1
   if mode=='lock':result(22)
   else:state['held']=True;result(0)
  elif j==2:
   assert a[0]==mutex and state['held']
   state['unlocks']+=1;state['held']=False;result(22 if mode=='unlock' else 0)
  elif j==3:
   assert a[0]==mutex and state['joins']==2 and not state['held']
   state['destroy']=True;result(16 if mode=='destroy' else 0)
  elif j==4:
   assert a[1]==0 and a[3]==mutex;state['creates']+=1;worker=state['creates']
   if mode=='create'+str(worker):result(11)
   else:
    handle=0 if mode=='null_handle' else 1 if mode=='same_handle' else worker
    u.mem_write(a[0],struct.pack('<Q',handle));state['saved']=u.context_save();state['worker']=worker
    u.reg_write(UC_ARM64_REG_SP,0x210000+worker*0x8000)
    for reg,v in ((UC_ARM64_REG_X19,0x1919),(UC_ARM64_REG_X20,0x2020),(UC_ARM64_REG_X21,0x2121),(UC_ARM64_REG_X22,0x2222),(UC_ARM64_REG_X29,0x2929),(UC_ARM64_REG_LR,0x300100),(UC_ARM64_REG_X0,mutex),(UC_ARM64_REG_PC,a[2])):u.reg_write(reg,v)
    return
  elif j==5:
   state['joins']+=1;assert a[0]==state['joins']
   u.mem_write(a[1],struct.pack('<Q',0 if mode=='result' else state['results'][a[0]]))
   if mode=='counter' and a[0]==2:u.mem_write(mutex+128,struct.pack('<Q',2047))
   result(22 if mode=='join'+str(a[0]) else 0)
  u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_INTR,syscall);u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(base+2048,base+65532,count=200000)
 assert state['exit']==expected,(mode,state)
 assert (b'M32 CHILD PASS' in b''.join(state['out']))==(mode=='valid')
 if mode=='valid':assert state['locks']==state['unlocks']==state['writes']==2048 and state['destroy'] and state['results']=={1:mutex,2:mutex}
 print('PASS mocked mutex:',mode)
