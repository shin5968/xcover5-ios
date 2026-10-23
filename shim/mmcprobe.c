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
    con_str("TEST", "register reads only; no commands");
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
    con_str("DONE", "photo screen; manual reboot");
}
