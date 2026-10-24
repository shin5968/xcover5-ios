"""Execute M36 ARM64 code with mocked libSystem/launchd calls, not a hardware test."""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/test-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
b=Path(sys.argv[1]).read_bytes();base=0x100000000
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6]
for side,mode,want in [('parent','ok',0),('child','ok',56),('parent','ppid',100),('parent','checkin',103),('parent','fork',106),('child','lookup',121),('parent','receive',109),('parent','body',110),('child','body',125),('child','send',123),('parent','wait',112)]:
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(base,0x10000);u.mem_write(base,b);u.mem_map(0x200000,0x10000);u.reg_write(UC_ARM64_REG_SP,0x20f000)
 u.mem_map(0x300000,0x10000);u.mem_write(0x300800,struct.pack('<I',10))
 slots=[0x300800]+[0x300000+16*j for j in range(1,13)]
 u.mem_write(base+0x4000,struct.pack('<13Q',*slots))
 child=False; exits=[];outputs=[];calls=[]
 def ret(v):u.reg_write(UC_ARM64_REG_X0,v&0xffffffffffffffff)
 def cstr(p):return bytes(u.mem_read(p,64)).split(b'\0')[0]
 def intr(uc,n,data):
  a=[u.reg_read(r) for r in regs];sc=u.reg_read(UC_ARM64_REG_X16)
  if sc==39:ret(2 if mode=='ppid' else 1)
  elif sc==1:exits.append(a[0]);u.emu_stop()
  elif sc==4:outputs.append(bytes(u.mem_read(a[1],a[2])));ret(a[2])
  elif sc==93:ret(0)
  else:raise AssertionError(sc)
 def imported(uc,pc,size,data):
  global child
  if not 0x300010<=pc<0x3000d0:return
  j=(pc-0x300000)//16;a=[u.reg_read(r) for r in regs];calls.append(j);ret(0)
  if j==10:ret(21 if child else 20)
  elif j==12:
   assert a[1]==4;u.mem_write(a[2],struct.pack('<I',50))
  elif j in (5,6):
   assert a[0]==50 and cstr(a[1])==b'org.xcover5.m36.echo'
   u.mem_write(a[2],struct.pack('<I',80 if j==6 else 60))
   if (j==5 and mode=='checkin') or (j==6 and mode=='lookup'):ret(1102)
  elif j==8:
   child=(side=='child');ret(-1 if mode=='fork' else (0 if child else 21))
   if child:u.mem_write(0x300800,struct.pack('<I',11))
  elif j==1:
   assert child and a[1]==1;u.mem_write(a[2],struct.pack('<I',70))
  elif j==3:
   assert a[5]==5000
   if a[1]==0x102:
    assert a[4]==(70 if child else 60) and a[3]==128
    vals=[0 if child else 18,32,0 if child else 90,a[4],0,0x4d35 if child else 0x4d34,0x456 if child else 0x123,20 if child else 21]
    if mode=='body':vals[6]=0
    u.mem_write(a[0],struct.pack('<8I',*vals))
    if mode=='receive':ret(0x10004003)
   else:
    assert a[1]==0x11 and a[2]==32
    v=struct.unpack('<8I',u.mem_read(a[0],32));assert v==((0x1513,32,80,70,0,0x4d34,0x123,21) if child else (18,32,90,0,0,0x4d35,0x456,20))
    if mode=='send':ret(0x10000004)
  elif j==9:
   assert a[0]==21 and a[2]==1;u.mem_write(a[1],struct.pack('<I',0x3800));ret(-1 if mode=='wait' else 21)
  elif j==4:assert a[1]==(70 if child else 60)
  elif j==7:assert child and a[1]==80
  elif j==11:assert a[:2]==[21,9]
  else:raise AssertionError(j)
  u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_INTR,intr);u.hook_add(UC_HOOK_CODE,imported)
 u.emu_start(base+2048,base+0x10000,count=100000)
 assert exits==[want],(side,mode,exits)
 text=b''.join(outputs)
 assert (b'M36 CHILD PASS' in text)==(side=='parent' and mode=='ok')
 assert (b'M36 PEER PASS' in text)==(side=='child' and mode=='ok')
 print('PASS',side,mode,'exit',want)
