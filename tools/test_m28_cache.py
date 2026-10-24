#!/usr/bin/env python3
"""AArch64 M28 probe and parent fault tests. Syscalls mocked, not hardware validation.
Usage: TEXT INIT_TEXT NM_LIST ORIGINAL_CACHE_DIRECTORY
"""
import json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_INTR
from unicorn.arm64_const import *
code=Path(sys.argv[1]).read_bytes();init=Path(sys.argv[2]).read_bytes()
labels={line.split()[2]:int(line.split()[0],16) for line in Path(sys.argv[3]).read_text().splitlines() if len(line.split())==3}
root=Path(sys.argv[4]);items=json.loads(Path(__file__).with_name('cache-layout.json').read_text())
fixtures={}
for item in items:
 with (root/item['file']).open('rb') as f:
  head=f.read(4096);f.seek(-4096,2);tail=f.read(4096)
 fixtures[item['file']]=(item['size'],head,tail)
regs=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]
def setup(text):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0x100000,0x10000);u.mem_write(0x100000,text)
 u.mem_map(0x200000,0x20000);u.reg_write(UC_ARM64_REG_SP,0x21fff0);u.reg_write(UC_ARM64_REG_X19,3)
 u.reg_write(UC_ARM64_REG_X30,0x10fff0)
 return u

def result(u,v,error=False):
 u.reg_write(UC_ARM64_REG_X0,v);u.reg_write(UC_ARM64_REG_NZCV,(u.reg_read(UC_ARM64_REG_NZCV)&~(1<<29))|((1<<29) if error else 0))
def string(u,p):return bytes(u.mem_read(p,180)).split(b'\0')[0].decode()
def probe(mode):
 u=setup(code);state={'exit':None,'reads':0,'opens':0,'name':None};out=[]
 def call(uc,intr,_):
  n=u.reg_read(UC_ARM64_REG_X16);a=[u.reg_read(r) for r in regs]
  def ret(v,e=False):result(u,v,e)
  if n==20:ret(1 if mode=='pid' else 17)
  elif n==5:
   name=string(u,a[0])
   if name=='/dev/console':assert a[1]==2;ret(3)
   else:
    assert a[1]==0 and name.startswith('/System/Library/Caches/com.apple.dyld/')
    state['name']=name.rsplit('/',1)[1];assert state['name']==items[state['opens']]['file'];state['opens']+=1
    ret(2,True) if mode=='open' else ret(6)
  elif n==199:
   assert a[:3]==[6,0,2];ret(fixtures[state['name']][0]+(1 if mode=='size' else 0))
  elif n==153:
   size,head,tail=fixtures[state['name']];assert a[0]==6 and a[2]==4096 and a[3] in (0,size-4096)
   state['reads']+=1
   data=bytearray(head if a[3]==0 else tail)
   if mode=='magic':data[0]^=1
   if mode=='head_crc' and a[3]==0:data[80]^=1
   if mode=='tail_crc' and a[3]:data[80]^=1
   if mode=='short':data=data[:-1]
   if mode=='pread_error':ret(5,True)
   else:u.mem_write(a[1],bytes(data));ret(len(data))
  elif n==6:assert a[0]==6;ret(0)
  elif n==4:assert a[0]==3;out.append(bytes(u.mem_read(a[1],a[2])));ret(a[2])
  elif n==1:state['exit']=a[0];u.emu_stop()
  else:raise AssertionError(n)
 u.hook_add(UC_HOOK_INTR,call);u.emu_start(0x100000,0x10fff0,count=100000000)
 expected={'valid':49,'pid':180,'open':181,'size':182,'magic':183,'short':183,'pread_error':183,'head_crc':184,'tail_crc':186}[mode]
 assert state['exit']==expected,(mode,state)
 if mode=='valid':assert state['reads']==86 and state['opens']==43 and b'43 cache files' in b''.join(out)
 else:assert b'PASS' not in b''.join(out)
 print('probe',mode,'PASS')
for mode in ('valid','pid','open','size','magic','short','pread_error','head_crc','tail_crc'):probe(mode)

def parent(mode,mount):
 u=setup(init);out=[];waits=0;killed=False
 def call(uc,intr,_):
  nonlocal waits,killed
  n=u.reg_read(UC_ARM64_REG_X16);a=[u.reg_read(r) for r in regs]
  def ret(v,e=False):result(u,v,e)
  if n==167:
   assert mount and string(u,a[0])=='hfs' and string(u,a[1])=='/System/Library/Caches/com.apple.dyld' and a[2]==1
   assert string(u,struct.unpack('<Q',u.mem_read(a[3],8))[0])=='/dev/xcuserdata'
   ret(6,True) if mode=='mount' else ret(0)
  elif n==5:
   assert mount and string(u,a[0]).endswith('/m28-cache-proof.txt') and a[1]==0
   ret(2,True) if mode=='open' else ret(6)
  elif n==3:
   assert mount and a[0]==6
   data=b'XCOVER5 M28 userdata cache volume verified\n'
   if mode=='content':data=b'!'+data[1:]
   if mode=='short':data=data[:-1]
   if mode=='read':ret(5,True)
   else:u.mem_write(a[1],data);ret(len(data))
  elif n==6:ret(0)
  elif n==4:assert a[0]==3;out.append(bytes(u.mem_read(a[1],a[2])).decode());ret(a[2])
  elif n==2:
   assert not mount;u.reg_write(UC_ARM64_REG_X1,1 if mode=='exec' else 0);ret(12,True) if mode=='fork' else ret(17)
  elif n==59:
   assert mode=='exec' and string(u,a[0])=='/emmc/sbin/m28-probe'
   assert struct.unpack('<QQ',u.mem_read(a[1],16))==(a[0],0) and bytes(u.mem_read(a[2],8))==bytes(8)
   ret(8,True)
  elif n==1:assert mode=='exec' and a[0]==127;u.emu_stop()
  elif n==7:
   assert a[0]==17 and a[2:]==[1,0];waits+=1
   if mode=='wait':ret(10,True)
   elif mode=='timeout':ret(0)
   elif mode=='eintr' and waits==1:ret(4,True)
   else:u.mem_write(a[1],struct.pack('<I',9 if mode=='signal' else 0x3100));ret(17)
  elif n==93:
   assert struct.unpack('<qI',u.mem_read(u.reg_read(UC_ARM64_REG_X4),12))==(0,100000);ret(0)
  elif n==37:assert a[:3]==[17,9,1];killed=True;ret(0)
  else:raise AssertionError(n)
 u.hook_add(UC_HOOK_INTR,call);u.emu_start(0x100000+labels['m28_mount' if mount else 'm28_test'],0x10fff0,count=200000)
 text=''.join(out)
 if mode in ('valid','eintr'):assert 'M28 USER PASS' in text,text
 elif mode=='exec':assert 'child exec errno=00000008' in text,text
 else:
  stage=({'mount':111,'open':112,'read':113,'content':114,'short':114} if mount else {'fork':101,'wait':102,'signal':103,'timeout':104})[mode]
  assert f'M28 USER FAIL stage={stage:08x}' in text and 'M28 USER PASS' not in text,text
 if mode=='timeout':assert waits==100 and killed
 if mount:assert u.reg_read(UC_ARM64_REG_X0)==(1 if mode=='valid' else 0)
 print('mount' if mount else 'parent',mode,'PASS')
for mode in ('valid','mount','open','read','content','short'):parent(mode,True)
for mode in ('valid','fork','wait','signal','timeout','eintr','exec'):parent(mode,False)
