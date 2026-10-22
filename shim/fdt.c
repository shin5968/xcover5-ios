/* Bounded FDT /chosen reader for Samsung's live bootloader tree. */
#include "fdt.h"
#define MAX_FDT_SIZE 0x100000U
static uint32_t be32(uintptr_t p)
{
    return __builtin_bswap32(*(volatile uint32_t *)p);
}
static int bounded_equal(uintptr_t p, uintptr_t end, const char *want)
{
    while (p < end) {
        char c = *(volatile const char *)p++;
        if (c != *want++) return 0;
        if (!c) return 1;
    }
    return 0;
}
int fdt_chosen_u64(uintptr_t fdt, const char *prop, uint64_t *out)
{
    if (!fdt || (fdt & 3) || be32(fdt) != 0xd00dfeed) return 0;
    uint32_t size = be32(fdt+4);
    if (size < 40 || size > MAX_FDT_SIZE || fdt+size < fdt) return 0;
    uint32_t so=be32(fdt+8), no=be32(fdt+12);
    uint32_t ns=be32(fdt+32), ss=be32(fdt+36);
    if ((so & 3) || so < 40 || no < 40 || so > size || no > size ||
        ss > size-so || ns > size-no) return 0;
    uintptr_t p=fdt+so, end=p+ss, names=fdt+no, names_end=names+ns;
    int depth=0, chosen=0;
    while (p <= end && end-p >= 4) {
        uint32_t token=be32(p); p+=4;
        if (token==1) {
            if (++depth > 64) return 0;
            if (depth==2) chosen=bounded_equal(p,end,"chosen");
            while (p<end && *(volatile const char *)p) p++;
            if (p==end) return 0;
            p=(p+4)&~(uintptr_t)3;
        } else if (token==2) {
            if (depth<=0) return 0;
            if (depth==2) chosen=0;
            depth--;
        } else if (token==3) {
            if (end-p<8 || depth<=0) return 0;
            uint32_t len=be32(p), off=be32(p+4); p+=8;
            if (len>end-p || off>=ns) return 0;
            if (chosen && depth==2 && bounded_equal(names+off,names_end,prop)) {
                if (len==4) *out=be32(p);
                else if (len==8) *out=((uint64_t)be32(p)<<32)|be32(p+4);
                else return 0;
                return 1;
            }
            p=(p+len+3)&~(uintptr_t)3;
        } else if (token==4) {
            continue;
        } else return 0;
    }
    return 0;
}
