#!/usr/bin/env python3
"""Compile and test the exact C on-disk parser from patch0036 on a host compiler.
Usage: python3 test_m20_view.py PATCH BOOT_IMAGE
Hardware read-sector calls are mocked. Actual kernel block I/O needs device testing.
"""
import ctypes as C
import struct, zlib, tempfile, subprocess, sys
from pathlib import Path
patch=Path(sys.argv[1]).read_text()
part=patch.split('+++ b/bsd/dev/xchfs.h\n',1)[1]
header=''.join(line[1:]+'\n' for line in part.splitlines() if line.startswith('+'))
strategy=header.split('static void xc_hfs_strategy(struct buf *bp)',1)[1].split('static int xc_hfs_psize',1)[0]
strategy='static void xc_hfs_strategy(struct buf *bp)'+strategy
boot=Path(sys.argv[2]).read_bytes()
FIRST,LAST,CAP=0x45000,0x5afff,0x747c000
po=2048+((struct.unpack_from('<I',boot,8)[0]+2047)//2048)*2048
n=struct.unpack_from('<I',boot,po+12)[0]
entry=po+0x2a8+(n-1)*32
vo=struct.unpack_from('<Q',boot,entry+16)[0]
base=FIRST*512+po+vo
size=16*1024*1024
prefix=r"""
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define XCHFS_HOST_TEST 1
#define printf(...) ((void)0)
typedef int64_t daddr64_t;
typedef char *caddr_t;
#define B_READ 1
struct buf { uint32_t n,resid; int flags,error,done,mapped; int64_t blk; char *data; };
static uint32_t buf_count(struct buf *b){return b->n;}
static int64_t buf_blkno(struct buf *b){return b->blk;}
static int buf_flags(struct buf *b){return b->flags;}
static void buf_setresid(struct buf *b,uint32_t r){b->resid=r;}
static int buf_map(struct buf *b,char **a){b->mapped=1;*a=b->data;return 0;}
static void buf_unmap(struct buf *b){b->mapped=0;}
static void buf_seterror(struct buf *b,int e){b->error=e;}
static void buf_biodone(struct buf *b){b->done=1;}
static int (*reader)(uint32_t,void *);
uint32_t xcover5_mmc_capacity(void){return 0x747c000;}
int xcover5_mmc_read_sector(uint32_t lba,void *p){return reader(lba,p);}
"""
suffix=r"""
void set_reader(int (*f)(uint32_t,void *)){reader=f;}
int discover(uint64_t *base,uint64_t *size){
 struct xc_hfs_view v;int e=xc_discover(&v);*base=v.base;*size=v.size;xc_view=v;return e;
}
int bytes_read(uint64_t off,void *out,uint32_t n){return xc_bytes(off,out,n);}
int strategy_test(int write,int64_t blk,uint32_t n,char *out){
 struct buf b={.n=n,.flags=write?0:B_READ,.blk=blk,.data=out};
 xc_hfs_strategy(&b);
 if(!b.done || b.mapped)return -100;
 if(b.resid!=(b.error?n:0))return -101;
 return b.error;
}
"""
with tempfile.TemporaryDirectory() as tmp:
    src=Path(tmp,'probe.c');src.write_text(prefix+header+strategy+suffix)
    so=Path(tmp,'probe.so')
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-variable','-shared','-fPIC',str(src),'-o',str(so)],check=True)
    lib=C.CDLL(str(so))
    CB=C.CFUNCTYPE(C.c_int,C.c_uint32,C.c_void_p)
    lib.set_reader.argtypes=[CB]
    lib.discover.argtypes=[C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)]
    lib.bytes_read.argtypes=[C.c_uint64,C.c_void_p,C.c_uint32]
    lib.strategy_test.argtypes=[C.c_int,C.c_int64,C.c_uint32,C.c_void_p]
    for mode,expected in [('valid',0),('header_crc',1),('layout',2),('table_crc',3),
                          ('duplicate',4),('range',4),('boot_magic',5),('kernel_overflow',5),
                          ('payload_magic',6),('segments',6),('extent',7),('hfs_magic',8),
                          ('hfs_size',8),('io_error',1)]:
        table=bytearray(16384);table[:16]=bytes(range(1,17))
        struct.pack_into('<QQ',table,32,FIRST,LAST)
        table[56:66]='boot\0'.encode('utf-16le')
        if mode=='duplicate':table[128:256]=table[:128]
        if mode=='range':struct.pack_into('<Q',table,40,CAP)
        h=bytearray(512);h[:8]=b'EFI PART'
        struct.pack_into('<II',h,8,0x10000,512)
        struct.pack_into('<QQQQ',h,24,1,CAP-1,34,CAP-34)
        struct.pack_into('<QIII',h,72,2,128,128,zlib.crc32(table))
        if mode=='layout':struct.pack_into('<I',h,80,0xffffffff)
        struct.pack_into('<I',h,16,zlib.crc32(h))
        if mode=='header_crc':h[100]^=1
        if mode=='table_crc':table[100]^=1
        disk=bytes(512)+h+table
        b=bytearray(boot)
        if mode=='boot_magic':b[0]^=1
        if mode=='kernel_overflow':struct.pack_into('<I',b,8,0xffffffff)
        if mode=='payload_magic':b[po]^=1
        if mode=='segments':struct.pack_into('<I',b,po+12,0xffffffff)
        if mode=='extent':struct.pack_into('<Q',b,entry+16,0xffffffffffffffff)
        if mode=='hfs_magic':b[po+vo+1024]^=1
        if mode=='hfs_size':struct.pack_into('>I',b,po+vo+1024+44,0xffffffff)
        @CB
        def read(lba,out):
            if mode=='io_error':return -1
            off=lba*512
            if off+512<=len(disk):data=disk[off:off+512]
            elif FIRST*512<=off and off+512<=FIRST*512+len(b):
                off-=FIRST*512;data=b[off:off+512]
            else:return -1
            C.memmove(out,bytes(data),512);return 0
        lib.set_reader(read)
        gotbase,gotsize=C.c_uint64(),C.c_uint64()
        rc=lib.discover(C.byref(gotbase),C.byref(gotsize))
        assert rc==expected,(mode,rc,expected)
        if not rc:
            assert (gotbase.value,gotsize.value)==(base,size)
            out=C.create_string_buffer(4096)
            assert lib.bytes_read(base+123,out,4096)==0
            assert out.raw==boot[po+vo+123:po+vo+123+4096]
            assert lib.strategy_test(0, 2, 4096, out)==0
            assert out.raw==boot[po+vo+1024:po+vo+1024+4096]
            assert lib.strategy_test(1, 0, 4096, out)==30 # EROFS, before mapping or reads
            assert lib.strategy_test(0, -1, 4096, out)==22
            assert lib.strategy_test(0, size//512, 4096, out)==22
            assert lib.strategy_test(0, 0, 1048577, out)==22
            assert lib.bytes_read(CAP*512-10,out,512)!=0
            assert lib.bytes_read(0,out,1048577)!=0
            print(f'{mode}: discovered unaligned HFS view {base:#x}, exact byte reads and bounds PASS')
        else:print(f'{mode}: rejected at stage {rc}')
