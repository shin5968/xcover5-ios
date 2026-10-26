/* XCover5-only USB log export. Board constants cross-checked with stock DT
 * and Samsung Exynos3830 source; see third_party/autoloop/ORIGIN.json.
 * Reuses the bootloader USB PHY state only after checking power/clocks.
 * A cold/disabled PHY is reported, not initialized with guessed writes.
 */
#include <pexpert/arm64/board_config.h>
#if defined(XCOVER5)
#include <sys/param.h>
#include <sys/systm.h>
#include <sys/proc_internal.h>
#include <kern/clock.h>
#include <kern/thread.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <arm/caches_internal.h>
#include <vm/pmap.h>
#include <vm/vm_kern.h>
#include <pexpert/pexpert.h>
#include <os/atomic_private.h>
extern vm_offset_t ml_io_map(vm_offset_t,vm_size_t);
extern ppnum_t pmap_find_phys(pmap_t,addr64_t);
static unsigned int xc_capture_lock;
static unsigned long xc_enter(void) {
    boolean_t enabled=ml_set_interrupts_enabled(FALSE);
    while(!os_atomic_cmpxchg(&xc_capture_lock,0,1,acquire)) {__asm__ volatile("yield");}
    return enabled;
}
static void xc_leave(unsigned long enabled) {
    os_atomic_store(&xc_capture_lock,0,release);
    ml_set_interrupts_enabled((boolean_t)enabled);
}
#include "xcover5_auto_capture.h"
void xcover5_log_byte(uint8_t c);
void xcover5_autolog_init(void);
void xcover5_test_finish(proc_t p,int rv);
void xcover5_log_byte(uint8_t c) {xc_capture(c);}
void xcover5_test_finish(proc_t p,int rv) {
    if(proc_getuid(p)!=0 || proc_ppid(p)!=1 || strcmp(p->p_comm,"m39-probe"))return;
    printf("XCOVER5 AUTO TEST_END pid=%d wait_status=%x\n",proc_getpid(p),rv);
    xc_finish(mach_absolute_time(),(uint32_t)rv);
    printf("XCOVER5 AUTO SNAPSHOT bytes=%u crc=%08x dropped=%u; awaiting PC ACK\n",
        xc_meta.size,xc_meta.crc,xc_meta.dropped);
}
static uint32_t usb_rd(vm_offset_t b,uint32_t off) {
    uint32_t v=*(volatile uint32_t *)(b+off);
    __asm__ volatile("dmb oshld" ::: "memory");return v;
}
static void board_wr(vm_offset_t b,uint32_t off,uint32_t v) {
    *(volatile uint32_t *)(b+off)=v;
    __asm__ volatile("dsb sy" ::: "memory");
}
static void xcover5_download_reset(void) {
    int enabled=0;PE_parse_boot_argn("xcautoreset",&enabled,sizeof(enabled));
    if(!enabled || !xc_meta.ready || !xc_acknowledged || xc_meta.dropped){
        printf("XCOVER5 AUTO: reset not armed\n");return;
    }
    vm_offset_t pmu=ml_io_map(0x11860000,0x4000);
    if(!pmu){printf("XCOVER5 AUTO: reset PMU map failed\n");return;}
    printf("XCOVER5 AUTO: PC acknowledged snapshot; download reset\n");
    /* sec_reboot: normal LPM magic, download reason; exynos reboot-v1:
     * SYSIP_DAT0 normal (sw reset), SYSTEM_CONFIGURATION SWRESET bit1.
     * No power-off, storage, partition or bootloader image writes. */
    ml_set_interrupts_enabled(FALSE);
    uint32_t magic=usb_rd(pmu,0x808);
    board_wr(pmu,0x808,(magic&~(0xffU<<16))|(0x4eU<<16));
    board_wr(pmu,0x80c,0x12345601);
    board_wr(pmu,0x810,0);
    board_wr(pmu,0x3a00,2);
    /* A failed reset never proceeds into another device operation. */
    for(;;){__asm__ volatile("wfe");}
}
static void xcover5_usb_gadget_start(vm_offset_t);
void xcover5_autolog_init(void) {
    int enabled=0;PE_parse_boot_argn("xcautousb",&enabled,sizeof(enabled));
    if(!enabled)return;
    vm_offset_t pmu=ml_io_map(0x11860000,0x4000);
    if(!pmu)return;
    uint32_t power=usb_rd(pmu,0x1c84);
    printf("XCOVER5 AUTO USB: HSI power status=%08x\n",power);
    /* Exynos3830 flexpmu hsi_status/hsi_on use mask BIT(0), not 0xf. */
    if(!(power&1U)){printf("XCOVER5 AUTO USB: STOP HSI power off\n");return;}
    vm_offset_t cmu=ml_io_map(0x13400000,0x4000);
    if(!cmu)return;
    uint32_t phy=usb_rd(cmu,0x203c),bus=usb_rd(cmu,0x2040);
    uint32_t ref50=usb_rd(cmu,0x200c),ref26=usb_rd(cmu,0x2010);
    printf("XCOVER5 AUTO USB: gates phy=%08x bus=%08x ref50=%08x ref26=%08x\n",phy,bus,ref50,ref26);
    if(!(phy&(1U<<21)) || !(bus&(1U<<21)) || !(ref26&(1U<<21))){
        printf("XCOVER5 AUTO USB: STOP bootloader clocks not retained\n");return;
    }
    vm_offset_t dwc=ml_io_map(0x13600000,0x10000);
    if(!dwc)return;
    uint32_t id=usb_rd(dwc,0xc120);
    printf("XCOVER5 AUTO USB: DWC3 id=%08x GCTL=%08x PHYCFG=%08x\n",id,usb_rd(dwc,0xc110),usb_rd(dwc,0xc200));
    if((id&0xffff0000U)!=0x55330000U){printf("XCOVER5 AUTO USB: STOP unknown controller\n");return;}
    xcover5_usb_gadget_start(dwc);
}
