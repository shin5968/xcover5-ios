/* M52: SDK-typed Apple CoreGraphics entry points, resolved after baseline. */
#ifndef XC_PANEL_COREGRAPHICS_H
#define XC_PANEL_COREGRAPHICS_H
#include <CoreGraphics/CoreGraphics.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static struct {
 __typeof__(&CGColorSpaceCreateDeviceRGB) space;
 __typeof__(&CGColorSpaceRelease) space_release;
 __typeof__(&CGBitmapContextCreate) create;
 __typeof__(&CGBitmapContextGetData) data;
 __typeof__(&CGBitmapContextGetWidth) width;
 __typeof__(&CGBitmapContextGetHeight) height;
 __typeof__(&CGBitmapContextGetBytesPerRow) row;
 __typeof__(&CGBitmapContextGetBitmapInfo) info;
 __typeof__(&CGContextRelease) release;
 __typeof__(&CGContextSetRGBFillColor) fill_color;
 __typeof__(&CGContextFillRect) rect;
 __typeof__(&CGContextFillEllipseInRect) ellipse;
 __typeof__(&CGContextSetRGBStrokeColor) stroke_color;
 __typeof__(&CGContextSetLineWidth) line_width;
 __typeof__(&CGContextMoveToPoint) move;
 __typeof__(&CGContextAddLineToPoint) line;
 __typeof__(&CGContextStrokePath) stroke;
 __typeof__(&CGContextFlush) flush;
} m52cg;
static int m52_load_cg(void) {
 fprintf(stderr,"XCOVER5 M52 PHASE dlopen CoreGraphics\n");
 void *h=dlopen("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",RTLD_NOW|RTLD_LOCAL);
 if(!h){fprintf(stderr,"M52 dlopen: %s\n",dlerror());return 1;}
#define M52_RESOLVE(field,symbol) do{dlerror();void *p=dlsym(h,symbol);const char *e=dlerror();if(e || !p){fprintf(stderr,"M52 symbol=%s error=%s\n",symbol,e?e:"null");return 2;}memcpy(&m52cg.field,&p,sizeof p);}while(0)
 M52_RESOLVE(space,"CGColorSpaceCreateDeviceRGB");M52_RESOLVE(space_release,"CGColorSpaceRelease");
 M52_RESOLVE(create,"CGBitmapContextCreate");M52_RESOLVE(data,"CGBitmapContextGetData");
 M52_RESOLVE(width,"CGBitmapContextGetWidth");M52_RESOLVE(height,"CGBitmapContextGetHeight");
 M52_RESOLVE(row,"CGBitmapContextGetBytesPerRow");M52_RESOLVE(info,"CGBitmapContextGetBitmapInfo");
 M52_RESOLVE(release,"CGContextRelease");M52_RESOLVE(fill_color,"CGContextSetRGBFillColor");
 M52_RESOLVE(rect,"CGContextFillRect");M52_RESOLVE(ellipse,"CGContextFillEllipseInRect");
 M52_RESOLVE(stroke_color,"CGContextSetRGBStrokeColor");M52_RESOLVE(line_width,"CGContextSetLineWidth");
 M52_RESOLVE(move,"CGContextMoveToPoint");M52_RESOLVE(line,"CGContextAddLineToPoint");
 M52_RESOLVE(stroke,"CGContextStrokePath");M52_RESOLVE(flush,"CGContextFlush");
#undef M52_RESOLVE
 puts("XCOVER5 M52 RESOLVE PASS:18 SDK-typed CoreGraphics functions");return 0;
}
static void m52_fill(CGContextRef c,double x,double y,double w,double h,double r,double g,double b) {
 m52cg.fill_color(c,r,g,b,1);m52cg.rect(c,(CGRect){{x,y},{w,h}});
}
static int m52_draw(uint32_t *p,unsigned frame) {
 frame%=16;
 fprintf(stderr,"XCOVER5 M52 PHASE colorspace frame=%u\n",frame+1);
 CGColorSpaceRef space=m52cg.space();if(!space)return 3;
 fprintf(stderr,"XCOVER5 M52 PHASE bitmap_create frame=%u\n",frame+1);
 CGContextRef c=m52cg.create(p,720,1480,8,2880,space,kCGImageAlphaPremultipliedFirst|kCGBitmapByteOrder32Little);
 m52cg.space_release(space);if(!c)return 4;
 if(m52cg.data(c)!=p || m52cg.width(c)!=720 || m52cg.height(c)!=1480 || m52cg.row(c)!=2880 ||
    m52cg.info(c)!=(kCGImageAlphaPremultipliedFirst|kCGBitmapByteOrder32Little)){m52cg.release(c);return 5;}
 fprintf(stderr,"XCOVER5 M52 PHASE draw frame=%u\n",frame+1);
 m52_fill(c,0,0,720,1480,0.04,0.08,0.16);
 /* Full-height exact-color rails also verify BGRA pixel order independently of Y origin. */
 m52_fill(c,0,0,8,1480,1,0,0);m52_fill(c,712,0,8,1480,0,0,1);
 m52_fill(c,40,120,640,1240,0.12,0.21,0.34);
 m52_fill(c,40,1280,640,80,0.18,0.48,0.72);
 m52_fill(c,64,176,592,28,0.05,0.1,0.17);
 m52_fill(c,64,176,(frame+1)*36,28,0.2,0.9,0.65);
 /* Native Quartz antialiased ellipses and paths, all in caller's IOSurface memory. */
 for(unsigned i=0;i<3;i++){
  m52cg.fill_color(c,0.22+i*0.22,0.75-i*0.18,0.92-i*0.12,1);
  m52cg.ellipse(c,(CGRect){{90+i*180,990},{130,130}});
 }
 m52_fill(c,92,340,536,540,0.06,0.12,0.2);
 for(unsigned i=0;i<6;i++)m52_fill(c,118+i*80,380,44,90+((frame+i*2)%12)*26,0.15,0.76,0.68);
 m52cg.stroke_color(c,1,0.78,0.22,1);m52cg.line_width(c,9);
 m52cg.move(c,110,720+(frame%4)*14);
 for(unsigned i=1;i<7;i++)m52cg.line(c,110+i*78,720+((frame+i*3)%7)*18);
 m52cg.stroke(c);m52cg.flush(c);m52cg.release(c);
 /* Verify actual memory writes, channel order, and complete opaque coverage. */
 for(unsigned y=0;y<1480;y++)if(p[y*720]!=0xffff0000U || p[y*720+719]!=0xff0000ffU)return 6;
 for(unsigned i=0;i<720U*1480U;i++)if((p[i]>>24)!=255)return 7;
 printf("XCOVER5 M52 DRAW PASS frame=%u direct_IOSurface_BGRA=1 opaque=1\n",frame+1);
 return 0;
}
#endif
