/* Bounded CMD8 metadata + CMD17 LBA0/1 reads only; no card writes. */
#include <stdint.h>
#include "console.h"
#define BASE 0x12100000UL
static uint32_t rd(unsigned o) { return *(volatile uint32_t *)(BASE+o); }
static void wr(unsigned o,uint32_t v) {
    *(volatile uint32_t *)(BASE+o)=v;
    __asm__ volatile("dsb sy" ::: "memory");
}
static uint64_t now(void) {
    uint64_t n;__asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(n));return n;
}

struct result { unsigned bytes; uint32_t irq, clear, response; };
static uint32_t word(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static int transfer(uint8_t *data, unsigned opcode, uint32_t argument, struct result *r)
{
 if(opcode!=8 && opcode!=17)return -5;
 uint64_t freq;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(freq));
 r->bytes=0;r->irq=0;r->clear=0;r->response=0;
 if(!freq || (rd(0x2c)&0x80000000U) || (rd(0x48)&0x200) ||
    (rd(0)&((1U<<25)|(1U<<5))) || ((rd(0x70)>>7)&7)!=2)return -1;
 wr(0,rd(0)|2);uint64_t start=now();
 while((rd(0)&2) && now()-start<freq){}
 if(rd(0)&2)return -2;
 wr(0x44,0xffff);r->clear=rd(0x44);
 if(r->clear&0xbfee)return -3;
 for(unsigned i=0;i<512;i++)data[i]=0;
 wr(0x1c,512);wr(0x20,512);wr(0x28,argument);wr(0x2c,0xa0002340U|opcode);
 start=now();
 while(now()-start<freq) {
  uint32_t irq=rd(0x44);r->irq|=irq;
  if(irq&0xbfc2)break;
  unsigned count=(rd(0x48)>>17)&0x1fff;
  while(count-- && r->bytes<512) {
   uint64_t value=*(volatile uint64_t *)(BASE+0x200);
   for(unsigned j=0;j<8;j++)data[r->bytes++]=(uint8_t)(value>>(j*8));
  }
  if(irq&0x20)wr(0x44,0x20);
  if(r->bytes==512 && (r->irq&12)==12)break;
 }
 r->response=rd(0x30);
 return r->bytes==512 && !(r->irq&0xbfc2) && (r->irq&12)==12 ? 0:-4;
}
static uint32_t hash(const uint8_t *p) {
 uint32_t h=2166136261U;for(unsigned i=0;i<512;i++)h=(h^p[i])*16777619U;return h;
}
static unsigned differences(const uint8_t *a,const uint8_t *b) {
 unsigned n=0;for(unsigned i=0;i<512;i++)n+=a[i]!=b[i];return n;
}

static uint64_t wide(const uint8_t *p) { return (uint64_t)word(p)|((uint64_t)word(p+4)<<32); }
static uint32_t crc32_header(const uint8_t *data,unsigned length) {
 uint32_t crc=~0U;
 for(unsigned i=0;i<length;i++) {
  crc^=(i>=16&&i<20)?0:data[i];
  for(unsigned j=0;j<8;j++)crc=(crc>>1)^((0U-(crc&1))&0xedb88320U);
 }
 return ~crc;
}
static int readblock(uint8_t *data,uint32_t lba,struct result *r) {
 int rc=transfer(data,17,lba,r);
 con_hex2("READ","lba=",lba,"rc=",(uint32_t)rc);
 con_hex2("STATUS","bytes=",r->bytes,"irq=",r->irq);
 con_hex("R1",r->response);
 if(!rc && (r->response&0xfdffa080U))return -6;
 return rc;
}
void mmc_block_probe(void)
{
 uint8_t ext[512],a[512],b[512];struct result r;
 con_str("TEST","read LBA0/1 twice; no writes");
 int rc=transfer(ext,8,0,&r);
 con_hex2("EXT_CSD","rc=",(uint32_t)rc,"irq=",r.irq);
 if(rc)return;
 uint32_t sectors=word(ext+212);
 con_hex2("CARD","access=",ext[179]&7,"sectors=",sectors);
 if((ext[179]&7) || ext[192]!=8 || sectors<=2) {
  con_str("STOP","user-area/capacity check failed");return;
 }
 for(uint32_t lba=0;lba<2;lba++) {
  if(readblock(a,lba,&r))return;
  if(readblock(b,lba,&r))return;
  unsigned diff=differences(a,b);
  con_hex2("REPEAT","diff=",diff,"hash=",hash(a));
  if(diff){con_str("STOP","unstable sector read");return;}
  if(lba==0) {
   con_hex2("MBR","sig=",(uint32_t)a[510]|((uint32_t)a[511]<<8),"type0=",a[450]);
  } else {
   con_hex2("GPT MAGIC","lo=",word(a),"hi=",word(a+4));
   if(word(a)!=0x20494645 || word(a+4)!=0x54524150) {
    con_str("STOP","no EFI PART signature");return;
   }
   unsigned size=word(a+12);
   con_hex2("HEADER","size=",size,"rev=",word(a+8));
   if(size<92 || size>512){con_str("STOP","invalid GPT header size");return;}
   uint32_t stored=word(a+16),computed=crc32_header(a,size);
   con_hex2("GPT CRC","stored=",stored,"calc=",computed);
   con_hex("CURRENT",wide(a+24));con_hex("BACKUP",wide(a+32));
   con_hex("FIRST USE",wide(a+40));con_hex("LAST USE",wide(a+48));
   con_hex("ENTRY LBA",wide(a+72));
   con_hex2("ENTRIES","count=",word(a+80),"size=",word(a+84));
   if(stored!=computed || wide(a+24)!=1 || wide(a+32)>=sectors) {
    con_str("STOP","GPT CRC or location invalid");return;
   }
   con_str("PASS","repeat + GPT header CRC match");
  }
 }
 con_str("DONE","photo full screen; manual reboot");
}

/* M15: fixed, bounded primary GPT table. Never issue media writes. */
static uint8_t entries[16384];
static uint32_t table_crc(const uint8_t *p,unsigned n) {
 uint32_t c=~0U;
 for(unsigned i=0;i<n;i++) {
  c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0U-(c&1))&0xedb88320U);
 }
 return ~c;
}
static int used(const uint8_t *p) {
 unsigned v=0;for(unsigned i=0;i<16;i++)v|=p[i];return v!=0;
}

#if SHIM_TEST == 10
static void boot_verify(void) {
 uint64_t start=0,end=0;unsigned found=0;struct result r;uint8_t a[512],b[512];
 for(unsigned i=0;i<128;i++) {
  const uint8_t *e=entries+i*128;
  if(used(e) && word(e+56)==0x006f0062 && word(e+60)==0x0074006f && e[64]==0 && e[65]==0) {
   start=wide(e+32);end=wide(e+40);found++;
  }
 }
 if(found!=1){con_str("STOP","boot partition missing/duplicate");return;}
 con_hex2("BOOT LBA","first=",(uint32_t)start,"last=",(uint32_t)end);
 if(transfer(a,17,(uint32_t)start,&r) || (r.response&0xfdffa080U))goto io;
 if(transfer(b,17,(uint32_t)start,&r) || (r.response&0xfdffa080U))goto io;
 if(differences(a,b) || word(a)!=0x52444e41 || word(a+4)!=0x2144494f ||
    word(a+36)!=2048 || word(a+40)!=2 || word(a+16)!=16384 || !word(a+8)) {
  con_str("STOP","unexpected/repeated boot header");return;
 }
 uint64_t offset=2048+(((uint64_t)word(a+8)+2047)&~2047ULL);
 if(offset+16384>(end-start+1)*512){con_str("STOP","payload outside boot");return;}
 con_hex2("HEADER","kernel=",word(a+8),"ramdisk=",word(a+16));
 con_hex("DATA OFFSET",offset);
 uint32_t crc=~0U;unsigned diff=0;
 for(unsigned sector=0;sector<32;sector++) {
  uint32_t lba=(uint32_t)(start+offset/512+sector);
  if(transfer(a,17,lba,&r) || (r.response&0xfdffa080U))goto io;
  if(transfer(b,17,lba,&r) || (r.response&0xfdffa080U))goto io;
  if(differences(a,b)){con_str("STOP","boot data repeat mismatch");return;}
  for(unsigned j=0;j<512;j++) {
   unsigned n=sector*512+j;
   uint8_t expected=(uint8_t)((n*73U)^(n>>3)^(n>>8)^0xa5U);
   diff+=a[j]!=expected;
   crc^=a[j];for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0U-(crc&1))&0xedb88320U);
  }
 }
 con_hex2("PAYLOAD","bytes=",16384,"diff=",diff);
 con_hex("DATA CRC",~crc);
 con_str(diff?"STOP":"PASS",diff?"test payload differs":"boot header + 16KiB match");
 con_str("DONE","photo screen; manual reboot");return;
io:con_str("STOP","boot MMC read/R1 failure");con_hex2("DETAIL","bytes=",r.bytes,"irq=",r.irq);
}
#endif

void mmc_table_probe(void) {
 uint8_t ext[512],h[512],again[512];struct result r;
 con_str("TEST","GPT table read twice; no writes");
 if(transfer(ext,8,0,&r) || (r.response&0xfdffa080U))goto io;
 uint32_t sectors=word(ext+212);
 if(ext[192]!=8 || (ext[179]&7) || sectors<34)goto bad;
 if(readblock(h,1,&r))goto io;
 if(word(h)!=0x20494645 || word(h+4)!=0x54524150 || word(h+8)!=0x10000 ||
    word(h+12)<92 || word(h+12)>512 || crc32_header(h,word(h+12))!=word(h+16) ||
    wide(h+24)!=1 || wide(h+32)!=sectors-1)goto bad;
 uint64_t first=wide(h+40),last=wide(h+48),base=wide(h+72);
 if(word(h+80)!=128 || word(h+84)!=128 || base<2 || base>=sectors ||
    base+32>first || first>last || last>=sectors-1)goto bad;
 for(unsigned i=0;i<32;i++) {
  uint8_t *dst=entries+i*512;
  if(transfer(dst,17,(uint32_t)base+i,&r) || (r.response&0xfdffa080U))goto io;
  if(transfer(again,17,(uint32_t)base+i,&r) || (r.response&0xfdffa080U))goto io;
  if(differences(dst,again)){con_str("STOP","table repeated read mismatch");return;}
 }
 uint32_t computed=table_crc(entries,sizeof(entries)),stored=word(h+88);
 con_hex2("TABLE CRC","stored=",stored,"calc=",computed);
 if(stored!=computed)goto bad;
 unsigned count=0;
 for(unsigned i=0;i<128;i++) {
  const uint8_t *e=entries+i*128;if(!used(e))continue;
  uint64_t a=wide(e+32),b=wide(e+40);
  if(a<first || a>b || b>last)goto bad;
  for(unsigned j=0;j<i;j++) {
   const uint8_t *q=entries+j*128;
   if(used(q) && a<=wide(q+40) && wide(q+32)<=b)goto bad;
  }
  count++;
 }
 if(!count)goto bad;
#if SHIM_TEST == 10
 boot_verify();return;
#endif
 uint64_t freq;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(freq));
 /* Eight entries per page, repeated indefinitely for photos. */
 for(;;) {
  unsigned index=0;
  for(unsigned page=0;page<(count+7)/8;page++) {
   con_clear(RED);con_str("SHIM","XCover5 M15 GPT partitions");
   con_hex2("PAGE","number=",page+1,"total=",(count+7)/8);
   con_hex2("TABLE CRC","stored=",stored,"calc=",computed);
   con_str("PASS","repeat + CRC + ranges/overlap");
   con_str("UNITS","hex LBA; size in hex MiB");
   for(unsigned shown=0;shown<8 && index<128;index++) {
    const uint8_t *e=entries+index*128;if(!used(e))continue;
    char name[37];unsigned k=0;
    for(;k<36;k++) {unsigned ch=e[56+k*2]|((unsigned)e[57+k*2]<<8);if(!ch)break;
     name[k]=(ch>=32 && ch<127)?(char)ch:'?';}
    name[k]=0;
    con_str("NAME",name);
    con_hex2("LBA","first=",(uint32_t)wide(e+32),"last=",(uint32_t)wide(e+40));
    con_hex2("SIZE","MiB=",(uint32_t)((wide(e+40)-wide(e+32)+1)/2048),"slot=",index+1);
    shown++;
   }
   con_str("NEXT","auto page in 20s; manual reboot");
   uint64_t start=now();while(now()-start<freq*20){}
  }
 }
io:con_str("STOP","MMC read/R1 error");con_hex2("DETAIL","bytes=",r.bytes,"irq=",r.irq);return;
bad:con_str("STOP","GPT metadata/CRC/range invalid");
}
