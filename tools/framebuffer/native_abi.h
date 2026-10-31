/* M68: HackiOS swap layout and fbscale=2 geometry; Samsung panel backend. */
#ifndef XC68_NATIVE_ABI_H
#define XC68_NATIVE_ABI_H
#define XC68_WIDTH 750U
#define XC68_HEIGHT 1624U
#define XC68_PANEL_W 720U
#define XC68_PANEL_H 1480U
#define XC68_PANEL_BYTES (XC68_PANEL_W*XC68_PANEL_H*4U)
static uint32_t xc68word(const uint8_t *p,unsigned off){uint32_t v;memcpy(&v,p+off,4);return v;}
static bool xc68_layer(uint32_t *panel,const uint8_t *pixels,uint64_t alloc,
 uint32_t width,uint32_t height,uint32_t stride,const uint8_t *src,const uint8_t *dst) {
 int64_t sx=(int32_t)xc68word(src,0),sy=(int32_t)xc68word(src,4);
 int64_t sw=(int32_t)xc68word(src,8),sh=(int32_t)xc68word(src,12);
 int64_t dx=(int32_t)xc68word(dst,0),dy=(int32_t)xc68word(dst,4);
 int64_t dw=(int32_t)xc68word(dst,8),dh=(int32_t)xc68word(dst,12);
 if(!panel||!pixels||!width||!height||width>2048||height>2048||stride<(uint64_t)width*4||
    stride>8192||(stride&3)||alloc<(uint64_t)stride*height||alloc>(8ULL<<20)||
    sx<0||sy<0||sw<=0||sh<=0||sx>=width||sy>=height||sw>width-sx||sh>height-sy||dw<=0||dh<=0)return false;
 /* Same destination-to-panel mapping as HackiOS drawLayer(fb_filter=0).
  * All coordinate arithmetic stays64-bit until clipped to the actual panel. */
 int64_t x0=dx*XC68_PANEL_W/XC68_WIDTH,y0=dy*XC68_PANEL_H/XC68_HEIGHT;
 int64_t x1=(dx+dw)*XC68_PANEL_W/XC68_WIDTH,y1=(dy+dh)*XC68_PANEL_H/XC68_HEIGHT;
 if(x1<=x0||y1<=y0)return true;
 int64_t left=x0<0?0:x0,right=x1>XC68_PANEL_W?XC68_PANEL_W:x1;
 int64_t top=y0<0?0:y0,bottom=y1>XC68_PANEL_H?XC68_PANEL_H:y1;
 for(int64_t y=top;y<bottom;y++) {
  int64_t source_y=sy+(y-y0)*sh/(y1-y0);
  const uint32_t *row=(const uint32_t *)(pixels+source_y*stride);
  for(int64_t x=left;x<right;x++)panel[y*XC68_PANEL_W+x]=row[sx+(x-x0)*sw/(x1-x0)];
 }
 return true;
}
#endif
