"""M38 ARM64 mocked API checks. Does not execute Apple notifyd."""
import sys, struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/test-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
binary=Path(sys.argv[1]).read_bytes()
for mode,want in [('ok',58),('parent',130),('register',131),('post',132),('timeout',133),('token',134),('cancel',135),('valid',136)]:
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);base=0x100000000
 u.mem_map(base,0x10000);u.mem_write(base,binary)
 u.mem_map(0x200000,0x10000);u.reg_write(UC_ARM64_REG_SP,0x20f000)
 u.mem_map(0x300000,0x10000)
 u.mem_write(base+0x4000,struct.pack('<5Q',*[0x300000+16*j for j in range(5)]))
 exits=[];calls=[]
 def ret(v):u.reg_write(UC_ARM64_REG_X0,v)
 def intr(uc,n,data):
  sc=u.reg_read(UC_ARM64_REG_X16)
  if sc==39:ret(2 if mode=='parent' else 1)
  elif sc==4:ret(u.reg_read(UC_ARM64_REG_X2))
  elif sc==1:exits.append(u.reg_read(UC_ARM64_REG_X0));u.emu_stop()
  else:raise AssertionError(sc)
 def call(uc,pc,size,data):
  if not 0x300000<=pc<0x300050:return
  j=(pc-0x300000)//16;calls.append(j)
  a=[u.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5]]
  ret(0)
  if j in (0,1):assert bytes(u.mem_read(a[0],29)).split(b'\0')[0]==b'org.xcover5.m38.notification'
  if j==0:
   assert a[2]==0;u.mem_write(a[1],struct.pack('<I',80));u.mem_write(a[3],struct.pack('<I',42))
   if mode=='register':ret(9)
  elif j==1:
   if mode=='post':ret(1)
  elif j==2:
   assert a[0]==42
   if mode=='cancel':ret(2)
  elif j==3:
   assert a[1:]==[0x102,0,128,80,5000]
   u.mem_write(a[0],struct.pack('<6I',0,24,0,80,0,43 if mode=='token' else 42))
   if mode=='timeout':ret(0x10004003)
  elif j==4:
   assert a[0]==42;ret(1 if mode=='valid' else 0)
  u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_INTR,intr);u.hook_add(UC_HOOK_CODE,call)
 u.emu_start(base+2048,base+len(binary),count=10000)
 assert exits==[want],(mode,exits)
 if mode=='ok':assert calls==[0,1,3,1,3,2,4],calls
 print('M38 mocked API',mode,'PASS',want)

