/* XCover5 DWMMC handoff snapshot. No controller writes or card commands.
 * Offsets: Linux drivers/mmc/host/dw_mmc.h. Base: stock DWMMC0 DT node.
 * Do NOT read FIFO/DATA: reading it would consume controller state.
 */
#include <stdint.h>
#include "console.h"
#define MMC_BASE 0x12100000UL
static inline uint32_t reg(unsigned offset)
{
    return *(volatile const uint32_t *)(MMC_BASE + offset);
}
#define SHOW(label, a, b) con_hex2(label, "a=", reg(a), "b=", reg(b))
void mmc_probe(void)
{
    con_str("TEST", SHIM_TEST == 5 ? "snapshot then CMD13 status only" : "register reads only; no commands");
    con_hex("MMC BASE", MMC_BASE);
    con_str("FIRST", "reading VERID/HCON");
    SHOW("VER/HCON", 0x06c, 0x070);
    SHOW("CTRL/PWR", 0x000, 0x004);
    SHOW("DIV/SRC", 0x008, 0x00c);
    SHOW("CLK/TYPE", 0x010, 0x018);
    SHOW("TMOUT/BLK", 0x014, 0x01c);
    SHOW("BYTE/IMSK", 0x020, 0x024);
    SHOW("ARG/CMD", 0x028, 0x02c);
    SHOW("RESP0/1", 0x030, 0x034);
    SHOW("RESP2/3", 0x038, 0x03c);
    SHOW("MINT/RINT", 0x040, 0x044);
    SHOW("STAT/FIFO", 0x048, 0x04c);
    SHOW("DETECT/WP", 0x050, 0x054);
    SHOW("TCB/TBB", 0x05c, 0x060);
    SHOW("UHS/RST", 0x074, 0x078);
    SHOW("BMOD", 0x080, 0x068);
    if (SHIM_TEST == 4) con_str("DONE", "photo screen; manual reboot");
}

#if SHIM_TEST == 5
static inline void put(unsigned offset, uint32_t value)
{
    *(volatile uint32_t *)(MMC_BASE + offset) = value;
    __asm__ volatile("dsb sy" ::: "memory");
}
static uint64_t ticks(void)
{
    uint64_t value;
    __asm__ volatile("isb; mrs %0, cntpct_el0" : "=r"(value));
    return value;
}
void mmc_status_probe(void)
{
    uint64_t freq;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(freq));
    con_str("CMD13", "status only; RCA=1 candidate");
    if (!freq || (reg(0x02c) & (1U<<31)) || (reg(0x048) & (1U<<9))) {
        con_str("STOP", "controller busy or no timer");
        return;
    }
    /* No card data transfer, reset, CMD6, partition switch or flash writes.
     * Clear only command completion/errors in host W1C status register. */
    const uint32_t done = 1U<<2;
    const uint32_t errors = (1U<<1)|(1U<<6)|(1U<<8)|(1U<<12);
    put(0x044, done | errors);
    put(0x028, 1U<<16);
    /* START | USE_HOLD_REG | WAIT_PRVDATA_COMPLETE | RESP_CRC | RESP_EXPECT | CMD13 */
    put(0x02c, (1U<<31)|(1U<<29)|(1U<<13)|(1U<<8)|(1U<<6)|13U);
    uint64_t start = ticks();
    uint32_t status;
    do {
        status=reg(0x044);
        if (status & (done|errors)) break;
    } while (ticks()-start < freq);
    con_hex2("RESULT", "irq=", status, "cmd=", reg(0x02c));
    con_hex("RESP0", reg(0x030));
    if (status & errors) con_str("CMD13", "host error; no retry/reset");
    else if (!(status & done)) con_str("CMD13", "timeout; no retry/reset");
    else {
        uint32_t r=reg(0x030);
        con_hex2("CARD", "state=", (r>>9)&15, "ready=", (r>>8)&1);
        con_str("CMD13", "response captured; inspect R1");
    }
    con_str("DONE", "photo screen; manual reboot");
}
#endif
