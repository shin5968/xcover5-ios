/* CMD8 EXT_CSD read only. No CMD6, CMD24/25, erase or partition switch. */
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
static int transfer(uint8_t *data, int split, struct result *r)
{
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
 wr(0x1c,512);wr(0x20,512);wr(0x28,0);wr(0x2c,0xa0002348U);
 start=now();
 while(now()-start<freq) {
  uint32_t irq=rd(0x44);r->irq|=irq;
  if(irq&0xbfc2)break;
  unsigned count=(rd(0x48)>>17)&0x1fff;
  while(count-- && r->bytes<512) {
   uint64_t value;
   if(split) {
    uint32_t lo=rd(0x200),hi=rd(0x204);
    value=(uint64_t)lo|((uint64_t)hi<<32);
   } else value=*(volatile uint64_t *)(BASE+0x200);
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
static void dump(const uint8_t *data) {
 /* Each word is little-endian. Labels identify exact EXT_CSD byte offsets. */
 for(unsigned i=176;i<224;i+=8) {
  char label[]="B000/004";
  label[1]='0'+i/100;label[2]='0'+i/10%10;label[3]='0'+i%10;
  unsigned j=i+4;label[5]='0'+j/100;label[6]='0'+j/10%10;label[7]='0'+j%10;
  con_hex2(label,"a=",word(data+i),"b=",word(data+i+4));
 }
}
void mmc_repeat_probe(void)
{
 uint8_t a[512],b[512],c[512];struct result r;int rc;
 con_str("TEST","3 EXT_CSD reads; no flash writes");
 con_hex("VERID",rd(0x6c));
 rc=transfer(a,0,&r);
 con_hex2("NATIVE A","rc=",(uint32_t)rc,"bytes=",r.bytes);
 con_hex2("A IRQ","clear=",r.clear,"seen=",r.irq);
 if(rc)return;
 rc=transfer(b,0,&r);
 con_hex2("NATIVE B","rc=",(uint32_t)rc,"bytes=",r.bytes);
 if(rc)return;
 con_hex2("REPEAT","diff=",differences(a,b),"hash=",hash(a));
 con_hex2("A FIELDS","rev=",a[192],"width=",a[183]);
 con_str("RAW A","little-endian words, byte offsets");dump(a);
 rc=transfer(c,1,&r);
 con_hex2("SPLIT32","rc=",(uint32_t)rc,"bytes=",r.bytes);
 con_hex2("C IRQ","clear=",r.clear,"seen=",r.irq);
 if(rc)return;
 con_hex2("COMPARE","diff=",differences(a,c),"hash=",hash(c));
 con_hex2("C FIELDS","rev=",c[192],"width=",c[183]);
 con_str("RAW C","32-bit lo@200 / hi@204");dump(c);
 con_str("DONE","photo full screen; manual reboot");
}
