/*
 * XCover5 (SM-G525N, Exynos 850) milestone 4 (diagnostics for m3 findings: SMP not visible, GIC groups):
 *   1. SMP: PSCI CPU_ON for cores 1..7 (MMU still off, so no cache aliasing)
 *   2. MMU on, 16K granule, identity map (see mmu.c)
 *   3. GICv2 + architected timer IRQs (virtual INTID 27, physical INTID 30)
 * Everything is printed on the bootloader framebuffer (0xfa000000); the
 * phone resets through PSCI afterwards.
 */
#include <stdint.h>
#include "console.h"
#include "mmu.h"
#if SHIM_TEST == 3
#include "loader.h"
#endif

#define GICD_BASE	0x12a01000UL	/* CPU GIC; 0x14af1000 is the ABOX audio GIC */
#define GICC_BASE	0x12a02000UL	/* CPU GIC; see interrupt-controller@12a00000 */

#define GICD_CTLR	0x000
#define GICD_IGROUPR	0x080
#define GICD_ISENABLER	0x100
#define GICD_ICENABLER	0x180
#define GICD_IPRIORITYR	0x400
#define GICD_ISPENDR	0x200
#define GICC_CTLR	0x000
#define GICC_PMR	0x004
#define GICC_BPR	0x008
#define GICC_IAR	0x00c
#define GICC_EOIR	0x010

#define VTIMER_INTID	27	/* DT timer: PPI 11 */
#define PTIMER_INTID	30	/* DT timer: PPI 14 (non-secure physical) */

#define PSCI_VERSION		0x84000000UL
#define PSCI_CPU_OFF		0x84000002UL
#define PSCI_CPU_ON		0xc4000003UL
#define PSCI_AFFINITY_INFO	0xc4000004UL
#define PSCI_SYSTEM_RESET	0x84000009UL
#define SMCCC_VERSION		0x80000000UL

#define NR_CPUS	8

#define rsr(r) ({ uint64_t _v; __asm__ volatile("mrs %0, " r : "=r"(_v)); _v; })
#define wsr(r, v) __asm__ volatile("msr " r ", %0" : : "r"((uint64_t)(v)))
#define isb() __asm__ volatile("isb" ::: "memory")

static inline uint32_t rd32(uintptr_t a) { return *(volatile uint32_t *)a; }
static inline void wr32(uintptr_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static inline void wr8(uintptr_t a, uint8_t v) { *(volatile uint8_t *)a = v; }

/* MPIDR affinity of each core, from the DTB: cpu0-3 = 0x000..0x300, cpu4-7 = 0x10000..0x10300 */
static const uint32_t cpu_aff[NR_CPUS] = { 0x0, 0x100, 0x200, 0x300, 0x10000, 0x10100, 0x10200, 0x10300 };

extern char secondary_entry[];
extern char _head[];

static const char *stage;	/* set at runtime: no absolute pointers in data */
/* Separate cache lines; secondary CPUs enter with MMU/cache off. */
struct cpu_result { volatile uint64_t mpidr; unsigned char pad[120]; };
static struct cpu_result sec_result[NR_CPUS] __attribute__((aligned(128)));
static volatile uint32_t irq_count, irq_other, irq_last;
static volatile int irq_src;

static uint64_t smc(uint64_t fn, uint64_t a1, uint64_t a2, uint64_t a3)
{
	register uint64_t x0 __asm__("x0") = fn;
	register uint64_t x1 __asm__("x1") = a1;
	register uint64_t x2 __asm__("x2") = a2;
	register uint64_t x3 __asm__("x3") = a3;
	__asm__ volatile("smc #0"
			 : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
			 :
			 : "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11",
			   "x12", "x13", "x14", "x15", "x16", "x17", "memory");
	return x0;
}

static uint64_t now(void)
{
	isb();
	return rsr("cntpct_el0");
}

static void delay_ms(unsigned ms)
{
	uint64_t end = now() + rsr("cntfrq_el0") / 1000 * ms;
	while (now() < end)
		;
}

static void __attribute__((noreturn)) reset(unsigned after_s)
{
	con_skip();
	con_str("RESET", "via PSCI soon");
	delay_ms(after_s * 1000);
	smc(PSCI_SYSTEM_RESET, 0, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
}

/* ---- exceptions ---- */

static void irq_handler(void)
{
	uint32_t iar = rd32(GICC_BASE + GICC_IAR);
	uint32_t id = iar & 0x3ff;

	if (id >= 1020)
		return;	/* spurious */
	irq_last = id;
	if (id == (uint32_t)irq_src)
		irq_count++;
	else
		irq_other++;
	if (id == VTIMER_INTID)
		wsr("cntv_tval_el0", rsr("cntfrq_el0") / 100);	/* 10 ms */
	else if (id == PTIMER_INTID)
		wsr("cntp_tval_el0", rsr("cntfrq_el0") / 100);
	wr32(GICC_BASE + GICC_EOIR, iar);
	isb();
}

void exc_handler(uint64_t slot, uint64_t *regs)
{
	if (slot == 5) {	/* IRQ from current EL, SPx */
		irq_handler();
		return;
	}
	con_clear(BLUE);
	switch (slot & 3) {
	case 0: con_str("PANIC", "SYNC"); break;
	case 1: con_str("PANIC", "IRQ"); break;
	case 2: con_str("PANIC", "FIQ"); break;
	default: con_str("PANIC", "SERROR"); break;
	}
	con_hex("SLOT", slot);
	con_hex("CPU", rsr("mpidr_el1"));
	con_str("STAGE", stage);
	con_hex("ESR", rsr("esr_el1"));
	con_hex("ELR", rsr("elr_el1"));
	con_hex("FAR", rsr("far_el1"));
	con_hex("SPSR", rsr("spsr_el1"));
	con_hex("X0", regs[0]);
	con_hex("X1", regs[1]);
	reset(60);
}

/* ---- SMP ---- */

void secondary_main(uint64_t idx)
{
	/* green bar below the yellow one written by start.S: C code is running */
	for (int i = 0; i < 64; i++)
		*(volatile uint32_t *)(FB_BASE + 1400UL * 2880 + 2048 + (idx << 13) + i * 4) = 0xff00ff00;
	if (idx >= NR_CPUS)
		for (;;) __asm__ volatile("wfe");
	sec_result[idx].mpidr = rsr("mpidr_el1") | (1ULL << 63);
	__asm__ volatile("dsb sy" ::: "memory");
	/* Stay online so AFFINITY_INFO can distinguish entry from CPU_OFF. */
	for (;;) __asm__ volatile("wfe");
}

static void __attribute__((unused)) test_smp(void)
{
	int64_t ret[NR_CPUS];

	stage = "smp";
	int64_t before[NR_CPUS];
	for (int i = 1; i < NR_CPUS; i++)
		before[i] = smc(PSCI_AFFINITY_INFO, cpu_aff[i], 0, 0);
	for (int i = 1; i < NR_CPUS; i++)
		ret[i] = smc(PSCI_CPU_ON, cpu_aff[i], (uintptr_t)secondary_entry, i);
	delay_ms(500);
	/* This test runs entirely with MMU and data cache OFF. */
	__asm__ volatile("dsb sy" ::: "memory");
	for (int i = 1; i < NR_CPUS; i++) {
		char label[] = "CPU0 ret";
		label[3] = '0' + i;
		con_hex2(label, "ret=", (uint32_t)ret[i], "mpidr=",
			 (uint32_t)sec_result[i].mpidr | (sec_result[i].mpidr ? 0 : 0xdead0000));
		con_hex2(" aff", "before=", (uint32_t)before[i], "after=", (uint32_t)smc(PSCI_AFFINITY_INFO, cpu_aff[i], 0, 0));
	}
}

/* ---- GICv2 + timer ---- */

static void irq_window(const char *label, int src)
{
	uint64_t f = rsr("cntfrq_el0");

	irq_count = irq_other = 0;
	irq_last = 0x3ff;
	irq_src = src;
	if (src == VTIMER_INTID) {
		wsr("cntv_tval_el0", f / 100);
		wsr("cntv_ctl_el0", 1);
	} else {
		wsr("cntp_tval_el0", f / 100);
		wsr("cntp_ctl_el0", 1);
	}
	isb();
	__asm__ volatile("msr daifclr, #2" ::: "memory");
	delay_ms(300);
	__asm__ volatile("msr daifset, #2" ::: "memory");
	wsr("cntv_ctl_el0", 0);
	wsr("cntp_ctl_el0", 0);
	isb();
	con_hex2(label, "irqs=", irq_count, "other=", irq_other);
	con_hex2(" last", "id=", irq_last, 0, 0);
}

static void __attribute__((unused)) test_gic(void)
{
	stage = "gic probe";
	/* Banked PPI/SGI registers first, then an SPI group, to see what the NS view can touch. */
	uint32_t g0 = rd32(GICD_BASE + GICD_IGROUPR), g1 = rd32(GICD_BASE + GICD_IGROUPR + 4);
	wr32(GICD_BASE + GICD_IGROUPR, g0 | (1U << VTIMER_INTID) | (1U << PTIMER_INTID));
	/* Leave all SPI groups untouched. */
	con_hex2("IGROUPR", "0=", g0, "1=", g1);
	con_hex2("IGROUPR", "w0=", rd32(GICD_BASE + GICD_IGROUPR), "w1=", rd32(GICD_BASE + GICD_IGROUPR + 4));
	wr32(GICD_BASE + GICD_ISENABLER, (1U << VTIMER_INTID) | (1U << PTIMER_INTID));
	/* Do not enable unrelated SPIs. */
	con_hex2("ISENABLE", "0=", rd32(GICD_BASE + GICD_ISENABLER), "1=", rd32(GICD_BASE + GICD_ISENABLER + 4));
	wr8(GICD_BASE + GICD_IPRIORITYR + 27, 0xa0);
	wr8(GICD_BASE + GICD_IPRIORITYR + PTIMER_INTID, 0xa0);
	con_hex2("IPRIO", "27=", rd32(GICD_BASE + GICD_IPRIORITYR + 24), "32=", rd32(GICD_BASE + GICD_IPRIORITYR + 32));
	wr32(GICD_BASE + GICD_CTLR, 1);
	wr32(GICC_BASE + GICC_PMR, 0xff);
	wr32(GICC_BASE + GICC_BPR, 0);
	wr32(GICC_BASE + GICC_CTLR, 1);
	con_hex2("CPUIF", "ctlr=", rd32(GICC_BASE + GICC_CTLR), "pmr=", rd32(GICC_BASE + GICC_PMR));
	/* vtimer: let it fire, look at the pending state with IRQs masked */
	wsr("cntv_tval_el0", rsr("cntfrq_el0") / 100);
	wsr("cntv_ctl_el0", 1);
	isb();
	delay_ms(30);
	con_hex2("VTIMER", "ctl=", rsr("cntv_ctl_el0"), "pend=", rd32(GICD_BASE + GICD_ISPENDR));
	con_hex2("HPPIR", "gicc=", rd32(GICC_BASE + 0x18), "isr=", rsr("isr_el1"));
	wsr("cntv_ctl_el0", 0);
	con_hex2("ITARGET", "0=", rd32(GICD_BASE + 0x800), "8=", rd32(GICD_BASE + 0x820));
	con_hex2("ICFGR", "1=", rd32(GICD_BASE + 0xc04), "2=", rd32(GICD_BASE + 0xc08));
	con_hex2("GICC", "apr0=", rd32(GICC_BASE + 0xd0), "rpr=", rd32(GICC_BASE + 0x14));
	wr32(GICC_BASE + GICC_PMR, 0x80);
	con_hex2("GICC", "pmr80=", rd32(GICC_BASE + GICC_PMR), "bpr=", rd32(GICC_BASE + GICC_BPR));
	/* SPI32 is read-only in this diagnostic. */
	con_hex2("SPI32", "en=", rd32(GICD_BASE + GICD_ISENABLER + 4), "tgt=", rd32(GICD_BASE + 0x820));
	/* Restore PMR after the 0x80 register probe: timer priority is 0xa0. */
	wr32(GICC_BASE + GICC_PMR, 0xff);
	__asm__ volatile("dsb sy; isb" ::: "memory");
	con_hex("IRQ PMR", rd32(GICC_BASE + GICC_PMR));
	/* IRQ window with the PMR wide open */
	stage = "gic vtimer";
	irq_window("VTIMER", VTIMER_INTID);
	stage = "gic ptimer";
	irq_window("PTIMER", PTIMER_INTID);
	wr32(GICD_BASE + GICD_ICENABLER, (1U << VTIMER_INTID) | (1U << PTIMER_INTID));
}
/* ---- main ---- */

/* Build two independent images; never execute HVC in these tests. */
#ifndef SHIM_TEST
#define SHIM_TEST 1
#endif
void mmc_ext_probe(void);
void mmc_probe(void);
void mmc_status_probe(void);
void shim_main(uint64_t dtb)
{
#if SHIM_TEST == 6
    stage = "DWMMC EXT_CSD read";
    con_clear(RED);
    con_str("SHIM", "XCover5 M12 EXT_CSD");
    mmc_ext_probe();
    for (;;) __asm__ volatile("wfe");
#endif
#if SHIM_TEST == 4 || SHIM_TEST == 5
    stage = "DWMMC0 read-only probe";
    con_clear(RED);
    con_str("SHIM", SHIM_TEST == 4 ? "XCover5 M10 MMC register probe" : "XCover5 M11 MMC status CMD13");
    con_hex("IMAGE", (uintptr_t)_head);
    con_hex("DTB", dtb);
    mmc_probe();
#if SHIM_TEST == 5
    stage = "DWMMC CMD13 status";
    mmc_status_probe();
#endif
    for (;;) __asm__ volatile("wfe");
#endif
#if SHIM_TEST == 3
    stage = "xnu loader";
    con_clear(RED);
    con_str("SHIM", "XCover5 XNU loader");
    con_str("ERROR", loader_boot(dtb));
    reset(120);
#endif
    stage = "console";
    con_clear(RED);
    con_str("SHIM", SHIM_TEST == 1 ? "xcover5 M7A SMP cache off" : "xcover5 M9 timer IRQ");
    con_hex("IMAGE", (uint64_t)_head);
    con_hex("DTB", dtb);
    con_hex("MPIDR", rsr("mpidr_el1"));
    con_hex("SCTLR", rsr("sctlr_el1"));
    con_hex("PSCI", smc(PSCI_VERSION, 0, 0, 0));
    con_hex("ENTRY", (uintptr_t)secondary_entry);
#if SHIM_TEST == 2
    con_hex2("CPU GIC", "d=", GICD_BASE, "c=", GICC_BASE);
#endif
#if SHIM_TEST == 1
    /* Fail closed: results would be ambiguous with cached primary memory. */
    if (rsr("sctlr_el1") & 5) {
        con_str("STOP", "MMU/cache enabled at entry");
    } else {
        con_str("TEST", "SMC CPU_ON; CPUs stay online");
        __asm__ volatile("dsb sy" ::: "memory");
        test_smp();
    }
#else
    stage = "mmu";
    struct mmu_info info;
    int rc = mmu_enable(&info);
    con_hex("MMU rc", (uint32_t)rc);
    if (!rc) {
        con_hex("PAR GICD", mmu_probe(GICD_BASE));
        con_hex("PAR GICC", mmu_probe(GICC_BASE));
        con_hex2("GIC ID", "d=", rd32(GICD_BASE + 0x008), "c=", rd32(GICC_BASE + 0xfc));
        test_gic();
    }
#endif
    stage = "done";
    con_str("DONE", "capture this screen");
    reset(120);
}
