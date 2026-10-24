#!/usr/bin/env python3
"""Execute actual M31 AArch64 instructions with mocked syscalls, NOT Apple dyld.
Usage: INIT_TEXT NM_LIST. Syscalls are mocked; this does not test Apple dyld.
"""
import struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_INTR
from unicorn.arm64_const import *
init=Path(sys.argv[1]).read_bytes()
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
 u=setup(init);out=[];waits=0;killed=False;spawned=False;exited=None;dups=[];selects=0;clocks=0;ticks=0x100000010
 child=mode in ('spawn','spawn_error','dup0','dup1','dup2')
 def call(uc,intr,_):
  nonlocal waits,killed,spawned,exited,selects,clocks,ticks
  n=u.reg_read(UC_ARM64_REG_X16);a=[u.reg_read(r) for r in regs]
  def ret(v,e=False):result(u,v,e)
  if n==4:out.append(bytes(u.mem_read(a[1],a[2])).decode());ret(a[2])
  elif n==2:u.reg_write(UC_ARM64_REG_X1,int(child));ret(12,True) if mode=='fork' else ret(17)
  elif n==90:
   assert a[0]==3 and a[1]==len(dups);dups.append(a[1]);ret(9,True) if mode=='dup'+str(a[1]) else ret(a[1])
  elif n==244:
   assert child and dups==[0,1,2] and a[0]==0 and string(u,a[1])==b'/emmc/sbin/m31-probe'
   desc=struct.unpack('<16Q',u.mem_read(a[2],128));assert desc[0]==184 and desc[2:]==(0,)*14
   expected=bytearray(256);struct.pack_into('<H',expected,0,0x40);struct.pack_into('<I',expected,108,2)
   assert bytes(u.mem_read(desc[1],256))==bytes(expected)
   assert struct.unpack('<QQ',u.mem_read(a[3],16))==(a[1],0)
   env,libs,inits,end=struct.unpack('<4Q',u.mem_read(a[4],32));assert end==0
   assert string(u,libs)==b'DYLD_PRINT_LIBRARIES=1' and string(u,inits)==b'DYLD_PRINT_INITIALIZERS=1'
   assert string(u,env)==b'DYLD_SHARED_CACHE_DIR=/System/Library/Caches/com.apple.dyld'
   spawned=True
   if mode=='spawn':u.emu_stop()
   else:ret(13,True)
  elif n==1:exited=a[0];u.emu_stop()
  elif n==7:
   assert a[0]==17 and a[2:4]==[1,0];waits+=1
   if mode=='wait':ret(10,True)
   elif mode in ('timeout','eintr_timeout','select_error','kill_error'):ret(4,True) if mode=='eintr_timeout' else ret(0)
   elif mode=='eintr' and waits==1:ret(4,True)
   else:u.mem_write(a[1],struct.pack('<I',9 if mode=='signal' else 0x3300 if mode=='wrong_exit' else 0x3400));ret(18 if mode=='wrong_pid' else 17)
  elif n==116:
   assert a[:2]==[0,0];clocks+=1
   if mode=='clock_error':ret(14,True)
   else:u.mem_write(a[2],struct.pack('<Q',ticks));ret(0)
  elif n==93:
   assert struct.unpack('<qI',u.mem_read(a[4],12))==(0,100000);selects+=1
   if mode=='select_error':ret(22,True)
   else:ticks+=2600000;ret(0)
  elif n==37:assert a[:3]==[17,9,1];killed=True;ret(3,True) if mode=='kill_error' else ret(0)
  else:raise AssertionError(n)
 u.hook_add(UC_HOOK_INTR,call);u.emu_start(0x100000+labels['m31_test'],0x10fff0,count=1000000)
 text=''.join(out)
 if mode in ('valid','eintr','clock_error'):assert 'M31 USER PASS' in text
 elif mode=='spawn':assert spawned and exited is None
 elif child:assert exited==127 and 'M31 child setup/exec errno=' in text
 else:
  stage={'fork':221,'wait':222,'signal':223,'wrong_exit':223,'wrong_pid':223,'timeout':224,'eintr_timeout':224,'select_error':224,'kill_error':224}[mode]
  assert f'M31 USER FAIL stage={stage:08x}' in text and 'M31 USER PASS' not in text,text
 if mode in ('timeout','eintr_timeout','select_error','kill_error'):
  assert waits==600 and selects==599 and killed
  assert f'timeout kill errno={3 if mode=="kill_error" else 0:08x}' in text
 if not child:
  assert clocks==2
  assert f'select_errors={selects if mode=="select_error" else 0:08x}' in text
  assert f'last_select_errno={22 if mode=="select_error" else 0:08x}' in text
  for which in ('start','end'):
   assert f'{which}_clock_errno={14 if mode=="clock_error" else 0:08x}' in text
  assert f'end_ticks_lo={0 if mode=="clock_error" else ticks&0xffffffff:08x}' in text
  assert f'start_ticks_hi={0 if mode=="clock_error" else 1:08x}' in text
  assert f'start_ticks_lo={0 if mode=="clock_error" else 16:08x}' in text
 print('parent',mode,'PASS')
for mode in ('valid','fork','wait','signal','wrong_exit','wrong_pid','timeout','eintr_timeout','eintr','spawn','spawn_error','dup0','dup1','dup2','select_error','clock_error','kill_error'):parent(mode)
