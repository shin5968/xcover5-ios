/* Validated XCover5 boot framebuffer contract; no MMIO or allocation. */
#ifndef XCOVER5_FB_LAYOUT_H
#define XCOVER5_FB_LAYOUT_H
struct xc_fb_layout {
    uint64_t physical, reserved, used;
    uint32_t width, height, stride;
};
/* Keep this bring-up mapping inside the already-used Samsung splash aperture.
 * ADT is not authority to map arbitrary MMIO. Pixel channel order is untested. */
static int xc_fb_layout_valid(const struct xc_fb_layout *f) {
    if (f->physical != 0xfa000000ULL ||
        f->reserved == 0 || f->reserved > 0x1400000ULL) return 0;
    if (f->width < 8 || f->height < 16 || f->width > 4096 || f->height > 4096) return 0;
    if ((f->stride & 3) || (uint64_t)f->stride < (uint64_t)f->width * 4) return 0;
    if (f->stride > 4096U * 4U) return 0;
    uint64_t used = (uint64_t)f->stride * f->height;
    if (used > f->reserved || f->used != used) return 0;
    return 1;
}
#endif
