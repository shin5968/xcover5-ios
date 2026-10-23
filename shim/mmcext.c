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
void mmc_ext_probe(void)
{
    uint64_t freq;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(freq));
    con_str("TEST","M12 EXT_CSD read; no flash writes");
    con_hex("VERID",rd(0x6c));
    con_hex2("BEFORE","cmd=",rd(0x2c),"stat=",rd(0x48));
    if (!freq || (rd(0x2c)&0x80000000U) || (rd(0x48)&0x200)) {
        con_str("STOP","controller busy/timer unavailable");return;
    }
    unsigned width=(rd(0x70)>>7)&7;
    con_hex("FIFO WIDTH",width);
    if (width!=1 && width!=2) { con_str("STOP","unsupported FIFO access width");return; }
    if (rd(0x00)&((1U<<25)|(1U<<5))) { con_str("STOP","DMA active; refusing takeover");return; }
    /* Only reset the HOST FIFO, preserving clocks, bus timing and card state. */
    wr(0x00,rd(0x00)|2);
    uint64_t start=now();
    while ((rd(0x00)&2) && now()-start<freq) {}
    if (rd(0x00)&2) {con_str("STOP","host FIFO reset timeout");return;}
    wr(0x44,0xffff);
    uint32_t clear=rd(0x44);
    con_hex("IRQ CLEAR",clear);
    if (clear&0xbfee) {con_str("STOP","status bits did not clear");return;}
    uint8_t data[512];
    for(unsigned i=0;i<512;i++)data[i]=0;
    wr(0x1c,512);wr(0x20,512);wr(0x28,0);
    /* eMMC SEND_EXT_CSD, response CRC, read data, hold register, wait prior data. */
    wr(0x2c,0xa0002348U);
    start=now();unsigned bytes=0;uint32_t irq=0,seen=0;
    while (now()-start<freq) {
        irq=rd(0x44);seen|=irq;
        if (irq&0xbfc2)break;
        unsigned count=(rd(0x48)>>17)&0x1fff;
        while (count-- && bytes<512) {
            uint64_t value;
            unsigned step=width==2?8:4;
            if(width==2)value=*(volatile uint64_t *)(BASE+0x200);
            else value=rd(0x200);
            for(unsigned j=0;j<step;j++)data[bytes++]=(uint8_t)(value>>(8*j));
        }
        if(irq&0x20)wr(0x44,0x20);
        if(bytes==512 && (seen&4) && (seen&8))break;
    }
    con_hex2("RESULT","bytes=",bytes,"irq=",seen);
    con_hex2("AFTER","cmd=",rd(0x2c),"stat=",rd(0x48));
    con_hex("RESP0",rd(0x30));
    if(bytes!=512 || (seen&0xbfc2) || (seen&12)!=12) {
        con_str("STOP","read incomplete/error; no retry");return;
    }
    uint32_t sectors=(uint32_t)data[212]|((uint32_t)data[213]<<8)|
        ((uint32_t)data[214]<<16)|((uint32_t)data[215]<<24);
    con_hex2("EXT_CSD","rev=",data[192],"part=",data[179]);
    con_hex2("CAPACITY","sectors=",sectors,"MiB=",sectors/2048);
    con_hex2("BUS/MODE","width=",data[183],"timing=",data[185]);
    uint32_t hash=2166136261U;
    for(unsigned i=0;i<512;i++)hash=(hash^data[i])*16777619U;
    con_hex("FNV1a",hash);
    con_str("DONE","EXT_CSD captured; photo screen");
}
