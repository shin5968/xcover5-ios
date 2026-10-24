#!/usr/bin/env python3
"""Host-compile the exact M28 parser/strategy; sparse fake disk, no device I/O."""
import ctypes as C
import struct,zlib,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def header(name,target):
 p=(ROOT/'xnu/patches'/name).read_text().split('+++ b/bsd/dev/'+target+'\n',1)[1]
 return ''.join(l[1:]+'\n' for l in p.splitlines() if l.startswith('+'))
h20=header('0036-xcover5-hfs-emmc-view.patch','xchfs.h')
h28=header('0038-xcover5-userdata-cache-view.patch','xcuserland.h')
strategy='static void xu_hfs_strategy(struct buf *bp)'+h28.split('static void xu_hfs_strategy(struct buf *bp)',1)[1].split('static int xu_hfs_psize',1)[0]
prefix='\n#include <stdint.h>\n#include <string.h>\n#include <errno.h>\n#define XCHFS_HOST_TEST 1\n#define printf(...) ((void)0)\ntypedef int64_t daddr64_t;\ntypedef char *caddr_t;\n#define B_READ 1\nstruct buf { uint32_t n,resid; int flags,error,done,mapped; int64_t blk; char *data; };\nstatic uint32_t buf_count(struct buf *b){return b->n;}\nstatic int64_t buf_blkno(struct buf *b){return b->blk;}\nstatic int buf_flags(struct buf *b){return b->flags;}\nstatic void buf_setresid(struct buf *b,uint32_t r){b->resid=r;}\nstatic int buf_map(struct buf *b,char **a){b->mapped=1;*a=b->data;return 0;}\nstatic void buf_unmap(struct buf *b){b->mapped=0;}\nstatic void buf_seterror(struct buf *b,int e){b->error=e;}\nstatic void buf_biodone(struct buf *b){b->done=1;}\nstatic int (*reader)(uint32_t,void *);\nuint32_t xcover5_mmc_capacity(void){return 0x747c000;}\nint xcover5_mmc_read_sector(uint32_t lba,void *p){return reader(lba,p);}\n'
suffix='\nvoid set_reader(int (*f)(uint32_t,void *)){reader=f;}\nint discover(uint64_t *base,uint64_t *size){\n struct xc_hfs_view v;int e=xu_discover(&v);*base=v.base;*size=v.size;xu_view=v;return e;\n}\nint bytes_read(uint64_t off,void *out,uint32_t n){return xc_bytes(off,out,n);}\nint strategy_test(int write,int64_t blk,uint32_t n,char *out){\n struct buf b={.n=n,.flags=write?0:B_READ,.blk=blk,.data=out};\n xu_hfs_strategy(&b);\n if(!b.done || b.mapped)return -100;\n if(b.resid!=(b.error?n:0))return -101;\n return b.error;\n}\n'
FIRST,LAST,CAP,SIZE=0xdab800,0x747b7ff,0x747c000,3*1024**3
with tempfile.TemporaryDirectory() as tmp:
 src=Path(tmp,'probe.c');src.write_text(prefix+h20+h28+strategy+suffix)
 so=Path(tmp,'probe.so')
 subprocess.run(['cc','-std=c11','-Wno-unused-function','-shared','-fPIC',str(src),'-o',str(so)],check=True)
 lib=C.CDLL(str(so));CB=C.CFUNCTYPE(C.c_int,C.c_uint32,C.c_void_p)
 lib.set_reader.argtypes=[CB];lib.discover.argtypes=[C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)]
 lib.strategy_test.argtypes=[C.c_int,C.c_int64,C.c_uint32,C.c_void_p]
 cases={'valid':0,'header_crc':1,'layout':2,'table_crc':3,'missing':3,'duplicate':4,'overlap':4,'range':4,'hfs_magic':5,'hfs_size':6,'partition_small':6,'dirty':7,'journal':7,'alternate':8,'io_error':1}
 for mode,expected in cases.items():
  table=bytearray(16384);table[:16]=bytes(range(1,17));struct.pack_into('<QQ',table,32,FIRST,LAST)
  table[56:74]='userdata\0'.encode('utf-16le')
  if mode=='missing':table[56]=0
  if mode=='duplicate':table[128:256]=table[:128]
  if mode=='overlap':
   table[128:256]=table[:128];table[184:202]='reserved\0'.encode('utf-16le')
  if mode=='range':struct.pack_into('<Q',table,40,CAP)
  if mode=='partition_small':struct.pack_into('<Q',table,40,FIRST+4095)
  h=bytearray(512);h[:8]=b'EFI PART';struct.pack_into('<II',h,8,0x10000,512)
  struct.pack_into('<QQQQ',h,24,1,CAP-1,34,CAP-34)
  struct.pack_into('<QIII',h,72,2,128,128,zlib.crc32(table))
  if mode=='layout':struct.pack_into('<I',h,80,0xffffffff)
  struct.pack_into('<I',h,16,zlib.crc32(h))
  if mode=='header_crc':h[100]^=1
  if mode=='table_crc':table[100]^=1
  disk=bytes(512)+h+table
  vh=bytearray(512);vh[:4]=b'HX\0\5';struct.pack_into('>I',vh,4,0x100);struct.pack_into('>II',vh,40,4096,SIZE//4096)
  alt=bytearray(vh)
  if mode=='hfs_magic':vh[0]=0
  if mode=='hfs_size':struct.pack_into('>I',vh,44,0xffffffff)
  if mode=='dirty':struct.pack_into('>I',vh,4,0)
  if mode=='journal':struct.pack_into('>I',vh,4,0x2100)
  if mode=='alternate':alt[104]^=1
  @CB
  def read(lba,out):
   if mode=='io_error':return -1
   off=lba*512
   if off+512<=len(disk):data=disk[off:off+512]
   elif off==FIRST*512+1024:data=vh
   elif off==FIRST*512+SIZE-1024:data=alt
   elif FIRST*512<=off<FIRST*512+SIZE:data=bytes(512)
   else:return -1
   C.memmove(out,bytes(data),512);return 0
  lib.set_reader(read);base,size=C.c_uint64(),C.c_uint64()
  rc=lib.discover(C.byref(base),C.byref(size));assert rc==expected,(mode,rc,expected)
  if not rc:
   assert (base.value,size.value)==(FIRST*512,SIZE)
   out=C.create_string_buffer(4096)
   for write,blk,n,e in [(0,2,512,0),(1,0,4096,30),(0,-1,4096,22),(0,SIZE//512,4096,22),(0,0,1048577,22),(0,SIZE//512,0,0)]:
    assert lib.strategy_test(write,blk,n,out)==e
  print(mode,rc,'PASS')
