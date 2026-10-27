/* M43 bring-up bounds. All inputs are kept64-bit until validated. */
#ifndef XC_SURFACE_BOUNDS_H
#define XC_SURFACE_BOUNDS_H
#define XC_SURFACE_MAX_ALLOC (8ULL << 20)
#define XC_SURFACE_BUDGET (32ULL << 20)
static bool xc_surface_shape(uint64_t width,uint64_t height,uint64_t bpe,
    uint64_t row,uint64_t alloc) {
    if (!width || !height || width>2048 || height>2048 || bpe!=4) return false;
    if (!row) row=(width*4+63)&~63ULL;
    if ((row&63) || row<width*4 || row>8192) return false;
    uint64_t needed=row*height;
    return needed<=XC_SURFACE_MAX_ALLOC && (!alloc || (alloc>=needed && alloc<=XC_SURFACE_MAX_ALLOC));
}
static bool xc_surface_reservable(uint64_t active,uint64_t bytes) {
    return bytes && bytes<=XC_SURFACE_MAX_ALLOC+PAGE_SIZE && active<=XC_SURFACE_BUDGET && bytes<=XC_SURFACE_BUDGET-active;
}
#endif
