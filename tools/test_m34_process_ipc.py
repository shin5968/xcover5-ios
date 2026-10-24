"""Execute M34 parent and peer instructions with mocked process/Mach APIs.
Distinct task IDs and port namespaces; this is not real kernel IPC/fork.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
b=Path(sys.argv[1]).read_bytes();base=0x100000000;slots=base+16384;ctx=slots+256
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6]
cases={'parent':55,'peer':55,'null':101,'allocate':102,'insert':103,'get':104,'set':105,'fork':106,'restore':107,'dealloc':108,'receive':109,'size':110,'complex':110,'local':110,'id':110,'body':110,'pid':110,'right':110,'reply_null':110,'send':111,'wait':112,'wait_status':112,'timeout':112,'destroy':113,'peer_get':121,'peer_allocate':122,'peer_send':123,'peer_receive':124,'peer_size':125,'peer_id':125,'peer_pid':125,'peer_body':125,'peer_destroy':126,'peer_dealloc':127}
for mode,expected in cases.items():
 peer=mode.startswith('peer');u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,65536);u.mem_write(base,b)
 u.mem_map(0x200000,65536);u.reg_write(UC_ARM64_REG_SP,0x20f000);u.mem_map(0x300000,65536)
 u.mem_write(slots,struct.pack('<12Q',*(0 if mode=='null' and j==3 else 0x300000+16*j for j in range(12))))
 u.mem_write(0x300000,struct.pack('<I',99))
 state={'forked':False,'sets':[],'sends':0,'receives':0,'waits':0,'killed':False,'destroyed':False,'out':[],'exit':None}
 def val(r):return u.reg_read(r)
 def result(v):u.reg_write(UC_ARM64_REG_X0,v&((1<<64)-1))
 def syscall(uc,intr,data):
  n=val(UC_ARM64_REG_X16)
  if n==1:state['exit']=val(UC_ARM64_REG_X0);u.emu_stop()
  elif n==4:state['out'].append(bytes(u.mem_read(val(UC_ARM64_REG_X1),val(UC_ARM64_REG_X2))));result(val(UC_ARM64_REG_X2));u.reg_write(UC_ARM64_REG_NZCV,0)
  elif n==93:assert struct.unpack('<qI',u.mem_read(val(UC_ARM64_REG_X4),12))==(0,100000);result(0);u.reg_write(UC_ARM64_REG_NZCV,0)
  else:raise AssertionError(n)
 def hook(uc,pc,size,data):
  if not 0x300000<=pc<0x3000c0:return
  j=(pc-0x300000)//16;a=[val(x) for x in regs];after=peer and state['forked'];task=555 if after else 99;port=321 if after else 123
  assert val(UC_ARM64_REG_SP)%16==0 and j!=0
  if j==1:
   assert a[:2]==[task,1];u.mem_write(a[2],struct.pack('<I',port));result(3 if mode==('peer_allocate' if after else 'allocate') else 0)
  elif j==2:assert a[:4]==[99,123,123,20];result(17 if mode=='insert' else 0)
  elif j==5:
   assert a[:2]==[task,4];u.mem_write(a[2],struct.pack('<I',444 if after else 777));result(5 if mode==('peer_get' if after else 'get') else 0)
  elif j==6:
   assert not after and a[:2]==[99,4];state['sets'].append(a[2]);assert a[2]==(123 if len(state['sets'])==1 else 777)
   result(5 if mode==('set' if len(state['sets'])==1 else 'restore') else 0)
  elif j==7:assert a[:2]==[task,444 if after else 777];result(5 if mode==('peer_dealloc' if after else 'dealloc') else 0)
  elif j==8:
   assert state['sets']==[123];state['forked']=True
   if peer:u.mem_write(0x300000,struct.pack('<I',555))
   result(-1 if mode=='fork' else 0 if peer else 202)
  elif j==10:result(202 if after else 101)
  elif j==3:
   assert a[5:]==[5000,0]
   if a[1]==0x11:
    assert a[2:5]==[32,0,0];state['sends']+=1
    words=struct.unpack('<8I',u.mem_read(a[0],32))
    assert words==((0x1513,32,444,321,0,0x4d34,0x123,202) if after else (18,32,999,0,0,0x4d35,0x456,101)),words
    result(0x10000004 if mode==('peer_send' if after else 'send') else 0)
   else:
    assert a[1:5]==[0x102,0,128,port];state['receives']+=1
    if not after:assert state['sets']==[123,777]
    words=[0,32,0,321,0,0x4d35,0x456,101] if after else [18,32,999,123,0,0x4d34,0x123,202]
    for name,idx in [('size',1),('local',3),('id',5),('body',6),('pid',7)]:
     if mode==('peer_'+name if after else name):words[idx]^=1
    if mode=='complex':words[0]|=0x80000000
    if mode=='right':words[0]=17
    if mode=='reply_null':words[2]=0
    u.mem_write(a[0],struct.pack('<8I',*words)+bytes(8));result(0x10004003 if mode==('peer_receive' if after else 'receive') else 0)
  elif j==9:
   assert a[:3]==[202,ctx+16,1];state['waits']+=1
   if state['killed']:result(0)
   elif mode=='wait':result(-1)
   elif mode=='timeout':result(0)
   else:u.mem_write(a[1],struct.pack('<I',0x3600 if mode=='wait_status' else 0x3700));result(202)
  elif j==11:assert not peer and a[:2]==[202,9] and mode not in ('parent','wait_status','destroy');state['killed']=True;result(0)
  elif j==4:assert a[:2]==[task,port];state['destroyed']=True;result(5 if mode==('peer_destroy' if after else 'destroy') else 0)
  else:raise AssertionError(j)
  u.reg_write(UC_ARM64_REG_PC,val(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_INTR,syscall);u.hook_add(UC_HOOK_CODE,hook);u.emu_start(base+2048,base+65532,count=100000)
 assert state['exit']==expected,(mode,state)
 text=b''.join(state['out'])
 assert (b'M34 CHILD PASS' in text)==(mode=='parent')
 assert (b'M34 PEER PASS' in text)==(mode=='peer')
 if mode in ('parent','peer'):assert state['sends']==state['receives']==1 and state['destroyed'] and not state['killed']
 if mode=='timeout':assert state['waits']==51 and state['killed']
 print('PASS mocked process IPC:',mode)
