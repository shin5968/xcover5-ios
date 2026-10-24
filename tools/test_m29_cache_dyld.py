#!/usr/bin/env python3
"""Execute actual M29 AArch64 instructions with mocked syscalls, NOT Apple dyld.
Usage: INIT_TEXT NM_LIST PROBE_TEXT. Hardware cache loading remains untested.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_INTR
from unicorn.arm64_const import *
init=Path(sys.argv[1]).read_bytes();code=Path(sys.argv[3]).read_bytes()
labels={s[2]:int(s[0],16) for line in Path(sys.argv[2]).read_text().splitlines() if len(s:=line.split())==3}
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4]
def setup(text):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0x100000,0x10000);u.mem_write(0x100000,text)
 u.mem_map(0x200000,0x20000);u.mem_write(0x200000,bytes([0xaa])*0x20000)
 u.reg_write(UC_ARM64_REG_SP,0x21f000);u.reg_write(UC_ARM64_REG_X19,3);u.reg_write(UC_ARM64_REG_X30,0x10fff0)
 return u
def result(u,v,e=False):
 u.reg_write(UC_ARM64_REG_X0,v);u.reg_write(UC_ARM64_REG_NZCV,(u.reg_read(UC_ARM64_REG_NZCV)&~(1<<29))|((1<<29) if e else 0))
def string(u,p):return bytes(u.mem_read(p,128)).split(b'\0')[0]
def parent(mode):
 u=setup(init);out=[];waits=0;killed=False;spawned=False;exited=None;dups=[]
 child=mode in ('spawn','spawn_error','dup0','dup1','dup2')
 def call(uc,intr,_):
  nonlocal waits,killed,spawned,exited
  n=u.reg_read(UC_ARM64_REG_X16);a=[u.reg_read(r) for r in regs]
  def ret(v,e=False):result(u,v,e)
  if n==4:out.append(bytes(u.mem_read(a[1],a[2])).decode());ret(a[2])
  elif n==2:u.reg_write(UC_ARM64_REG_X1,int(child));ret(12,True) if mode=='fork' else ret(17)
  elif n==90:
   assert a[0]==3 and a[1]==len(dups);dups.append(a[1]);ret(9,True) if mode=='dup'+str(a[1]) else ret(a[1])
  elif n==244:
   assert child and dups==[0,1,2] and a[0]==0 and string(u,a[1])==b'/emmc/sbin/m29-probe'
   desc=struct.unpack('<16Q',u.mem_read(a[2],128));assert desc[0]==184 and desc[2:]==(0,)*14
   expected=bytearray(256);struct.pack_into('<H',expected,0,0x40);struct.pack_into('<I',expected,108,2)
   assert bytes(u.mem_read(desc[1],256))==bytes(expected)
   assert struct.unpack('<QQ',u.mem_read(a[3],16))==(a[1],0)
   env,end=struct.unpack('<QQ',u.mem_read(a[4],16));assert end==0
   assert string(u,env)==b'DYLD_SHARED_CACHE_DIR=/System/Library/Caches/com.apple.dyld'
   spawned=True
   if mode=='spawn':u.emu_stop()
   else:ret(13,True)
  elif n==1:exited=a[0];u.emu_stop()
  elif n==7:
   assert a[0]==17 and a[2:4]==[1,0];waits+=1
   if mode=='wait':ret(10,True)
   elif mode in ('timeout','eintr_timeout'):ret(4,True) if mode=='eintr_timeout' else ret(0)
   elif mode=='eintr' and waits==1:ret(4,True)
   else:u.mem_write(a[1],struct.pack('<I',9 if mode=='signal' else 0x3100 if mode=='wrong_exit' else 0x3200));ret(18 if mode=='wrong_pid' else 17)
  elif n==93:assert struct.unpack('<qI',u.mem_read(a[4],12))==(0,100000);ret(0)
  elif n==37:assert a[:3]==[17,9,1];killed=True;ret(0)
  else:raise AssertionError(n)
 u.hook_add(UC_HOOK_INTR,call);u.emu_start(0x100000+labels['m29_test'],0x10fff0,count=1000000)
 text=''.join(out)
 if mode in ('valid','eintr'):assert 'M29 USER PASS' in text
 elif mode=='spawn':assert spawned and exited is None
 elif child:assert exited==127 and 'M29 child setup/exec errno=' in text
 else:
  stage={'fork':201,'wait':202,'signal':203,'wrong_exit':203,'wrong_pid':203,'timeout':204,'eintr_timeout':204}[mode]
  assert f'M29 USER FAIL stage={stage:08x}' in text and 'M29 USER PASS' not in text,text
 if 'timeout' in mode:assert waits==600 and killed
 print('parent',mode,'PASS')
def probe(mode):
 u=setup(code);out=[];exited=None
 u.mem_map(0x300000,0x10000);u.mem_write(0x300000,b'dyld_v1 ' if mode!='cache_magic' else b'badcache')
 u.mem_write(0x200000,b'/emmc/sbin/m29-probe\0');u.mem_write(0x200100,struct.pack('<QQ',0x200000,0))
 u.reg_write(UC_ARM64_REG_X0,2 if mode=='argc' else 1);u.reg_write(UC_ARM64_REG_X1,0x200100)
 def call(uc,intr,_):
  nonlocal exited
  n=u.reg_read(UC_ARM64_REG_X16);a=[u.reg_read(r) for r in regs]
  def ret(v,e=False):result(u,v,e)
  if n==20:ret(1 if mode=='pid' else 17)
  elif n==294:
   assert bytes(u.mem_read(a[0],8))==bytes(8)
   u.mem_write(a[0],struct.pack('<Q',0 if mode=='cache_null' else 0x300000));ret(12,True) if mode=='cache_error' else ret(0)
  elif n==5:
   name=string(u,a[0]);assert (name,a[1]) in ((b'/dev/console',2),(b'/emmc/m20-proof.txt',0))
   ret(2,True) if mode=='open' else ret(3 if name==b'/dev/console' else 6)
  elif n==3:
   data=b'XCOVER5 M20 eMMC file read verified\n'
   if mode=='content':data=b'!'+data[1:]
   if mode=='short':data=data[:-1]
   u.mem_write(a[1],data);ret(5,True) if mode=='read' else ret(len(data))
  elif n==6:ret(0)
  elif n==4:out.append(bytes(u.mem_read(a[1],a[2])));ret(5,True) if mode=='write' else ret(a[2])
  elif n==1:exited=a[0];u.emu_stop()
  else:raise AssertionError(n)
 u.hook_add(UC_HOOK_INTR,call);u.emu_start(0x100000,0x10fff0,count=100000)
 assert exited==(50 if mode=='valid' else 111),(mode,exited)
 if mode=='valid':assert b'M29 CHILD PASS' in b''.join(out)
 print('probe',mode,'PASS')
for mode in ('valid','fork','wait','signal','wrong_exit','wrong_pid','timeout','eintr_timeout','eintr','spawn','spawn_error','dup0','dup1','dup2'):parent(mode)
for mode in ('valid','argc','pid','cache_error','cache_null','cache_magic','open','content','short','read','write'):probe(mode)
