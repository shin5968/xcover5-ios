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
