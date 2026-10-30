/* M53 explicitly supplied outline font, native CoreText glyph mapping/drawing. */
#ifndef XC_PANEL_CORETEXT_H
#define XC_PANEL_CORETEXT_H
#include "panel-coregraphics.h"
#include "panel-font.h"
#include <CoreText/CoreText.h>
#include <math.h>
static struct {
 __typeof__(&CGDataProviderCreateWithData) provider;
 __typeof__(&CGDataProviderRelease) provider_release;
 __typeof__(&CGFontCreateWithDataProvider) font;
 __typeof__(&CGFontRelease) font_release;
 __typeof__(&CGContextSetTextMatrix) matrix;
 __typeof__(&CGContextSetTextDrawingMode) mode;
 __typeof__(&CTFontCreateWithGraphicsFont) ctfont;
 __typeof__(&CTFontGetGlyphsForCharacters) glyphs;
 __typeof__(&CTFontGetAdvancesForGlyphs) advances;
 __typeof__(&CTFontDrawGlyphs) draw;
 __typeof__(&CTFontCopyPostScriptName) name;
} m53ct;
static int m53_load_text(void) {
 if(m52_load_cg())return 1;
 fprintf(stderr,"XCOVER5 M53 PHASE dlopen CoreText\n");
 void *ct=dlopen("/System/Library/Frameworks/CoreText.framework/CoreText",RTLD_NOW|RTLD_LOCAL);
 if(!ct){fprintf(stderr,"M53 dlopen: %s\n",dlerror());return 2;}
 void *cg=dlopen("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",RTLD_NOW|RTLD_LOCAL);
 if(!cg)return 2;
#define M53_RESOLVE(h,field,symbol) do{dlerror();void *p=dlsym(h,symbol);const char *e=dlerror();if(e || !p){fprintf(stderr,"M53 symbol=%s error=%s\n",symbol,e?e:"null");return 3;}memcpy(&m53ct.field,&p,sizeof p);}while(0)
 M53_RESOLVE(cg,provider,"CGDataProviderCreateWithData");M53_RESOLVE(cg,provider_release,"CGDataProviderRelease");
 M53_RESOLVE(cg,font,"CGFontCreateWithDataProvider");M53_RESOLVE(cg,font_release,"CGFontRelease");
 M53_RESOLVE(cg,matrix,"CGContextSetTextMatrix");M53_RESOLVE(cg,mode,"CGContextSetTextDrawingMode");
 M53_RESOLVE(ct,ctfont,"CTFontCreateWithGraphicsFont");M53_RESOLVE(ct,glyphs,"CTFontGetGlyphsForCharacters");
 M53_RESOLVE(ct,advances,"CTFontGetAdvancesForGlyphs");M53_RESOLVE(ct,draw,"CTFontDrawGlyphs");M53_RESOLVE(ct,name,"CTFontCopyPostScriptName");
#undef M53_RESOLVE
 puts("XCOVER5 M53 RESOLVE PASS:11 SDK-typed glyph functions; embedded owned font");return 0;
}
static int m53_line(CGContextRef c,CTFontRef font,const char *text,double x,double y) {
 size_t n=strlen(text);if(!n || n>64)return 1;
 UniChar chars[64];CGGlyph glyphs[64];CGSize advances[64];CGPoint positions[64];
 for(size_t i=0;i<n;i++){if((unsigned char)text[i]>=128)return 2;chars[i]=(unsigned char)text[i];}
 if(!m53ct.glyphs(font,chars,glyphs,(CFIndex)n))return 3;
 double width=m53ct.advances(font,kCTFontOrientationHorizontal,glyphs,advances,(CFIndex)n);
 if(!isfinite(width) || width<=0 || x<16 || x+width>704)return 4;
 for(size_t i=0;i<n;i++){
  if(!glyphs[i] || !isfinite(advances[i].width) || advances[i].width<=0)return 5;
  positions[i]=(CGPoint){x,y};x+=advances[i].width;
 }
 m53ct.draw(font,glyphs,positions,n,c);return 0;
}
static unsigned m53_white(const uint32_t *p) {
 unsigned count=0;for(unsigned i=0;i<720U*1480U;i++)count+=p[i]==0xffffffffU;return count;
}
static int m53_draw(uint32_t *p,unsigned frame) {
 if(m52_draw(p,frame))return 1;
 unsigned before=m53_white(p);if(before)return 2;
 fprintf(stderr,"XCOVER5 M53 PHASE provider_font frame=%u\n",frame+1);
 CGDataProviderRef provider=m53ct.provider(NULL,m53_font_bytes,sizeof m53_font_bytes,NULL);if(!provider)return 3;
 CGFontRef graphics=m53ct.font(provider);m53ct.provider_release(provider);if(!graphics)return 4;
 fprintf(stderr,"XCOVER5 M53 PHASE ctfont frame=%u\n",frame+1);
 CTFontRef font=m53ct.ctfont(graphics,44,NULL,NULL);m53ct.font_release(graphics);if(!font)return 5;
 CFStringRef name=m53ct.name(font);int identity=name && CFStringCompare(name,CFSTR("XCoverPanelTest-Regular"),0)==kCFCompareEqualTo;
 if(name)CFRelease(name);if(!identity){CFRelease(font);return 11;}
 CGColorSpaceRef space=m52cg.space();if(!space){CFRelease(font);return 6;}
 CGContextRef c=m52cg.create(p,720,1480,8,2880,space,kCGImageAlphaPremultipliedFirst|kCGBitmapByteOrder32Little);
 m52cg.space_release(space);if(!c){CFRelease(font);return 6;}
 if(m52cg.data(c)!=p){m52cg.release(c);CFRelease(font);return 6;}
 fprintf(stderr,"XCOVER5 M53 PHASE glyph_draw frame=%u\n",frame+1);
 m53ct.matrix(c,(CGAffineTransform){1,0,0,1,0,0});m53ct.mode(c,kCGTextFill);m52cg.fill_color(c,1,1,1,1);
 char counter[32];snprintf(counter,sizeof counter,"FRAME %02u / 16",frame+1);
 int rc=m53_line(c,font,"CORETEXT M53",70,1300);
 if(!rc)rc=m53_line(c,font,"XCOVER5 IOS",70,1190);
 if(!rc)rc=m53_line(c,font,counter,70,930);
 if(!rc)rc=m53_line(c,font,"720 X 1480 BGRA",70,285);
 if(!rc)rc=m53_line(c,font,"SURFACE READY",70,225);
 m52cg.flush(c);m52cg.release(c);CFRelease(font);if(rc)return 7;
 unsigned after=m53_white(p);if(after<500)return 8;
 for(unsigned y=0;y<1480;y++)if(p[y*720]!=0xffff0000U || p[y*720+719]!=0xff0000ffU)return 9;
 for(unsigned i=0;i<720U*1480U;i++)if((p[i]>>24)!=255)return 10;
 printf("XCOVER5 M53 TEXT PASS frame=%u glyph_pixels=%u embedded_font=1\n",frame+1,after);
 return 0;
}
#endif
