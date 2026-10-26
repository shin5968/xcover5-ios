/* XCover5 immutable test snapshot. Platform supplies xc_enter/xc_leave.
 * No I/O, allocation, printf, or device writes from the console callback. */
#ifndef XC_AUTO_CAPTURE_H
#define XC_AUTO_CAPTURE_H
#define XC_LOG_CAP (1024U * 1024U)
#define XC_CHUNK 256U
struct xc_meta {
    uint64_t magic, run;
    uint32_t version, ready, size, crc, dropped, status;
};
_Static_assert(sizeof(struct xc_meta)==40,"wire metadata ABI");
static unsigned char xc_log[XC_LOG_CAP];
static struct xc_meta xc_meta = {0x31474f4c4358ULL,0,1,0,0,0,0,0};
static int xc_frozen, xc_acknowledged;
static uint32_t xc_crc32(const unsigned char *s,uint32_t n) {
    uint32_t c=~0U;
    for(uint32_t i=0;i<n;i++) {
        c^=s[i];
        for(unsigned j=0;j<8;j++) c=(c>>1)^((0U-(c&1U))&0xedb88320U);
    }
    return ~c;
}
static void xc_capture(unsigned char c) {
    unsigned long state=xc_enter();
    if(!xc_frozen) {
        if(xc_meta.size<XC_LOG_CAP) xc_log[xc_meta.size++]=c;
        else if(xc_meta.dropped!=UINT32_MAX) xc_meta.dropped++;
    }
    xc_leave(state);
}
static void xc_finish(uint64_t run,uint32_t status) {
    unsigned long state=xc_enter();
    if(xc_frozen){xc_leave(state);return;}
    xc_frozen=1;xc_meta.run=run;xc_meta.status=status;
    xc_leave(state);
    uint32_t crc=xc_crc32(xc_log,xc_meta.size);
    state=xc_enter();xc_meta.crc=crc;xc_meta.ready=1;xc_leave(state);
}
/* Exact frozen identity, size and checksum are required before reset is armed. */
static int xc_ack(const unsigned char *p,uint32_t n) {
    struct xc_meta got;
    if(n!=sizeof(got))return 0;
    memcpy(&got,p,sizeof(got));
    unsigned long state=xc_enter();
    int ok=xc_meta.ready && !xc_meta.dropped && !memcmp(&got,&xc_meta,sizeof(got));
    if(ok)xc_acknowledged=1;
    xc_leave(state);return ok;
}
static uint32_t xc_read_log(uint32_t offset,unsigned char *out,uint32_t max) {
    if(!xc_meta.ready || offset>xc_meta.size)return 0;
    uint32_t n=xc_meta.size-offset;
    if(n>max)n=max;
    memcpy(out,xc_log+offset,n);return n;
}
#endif
