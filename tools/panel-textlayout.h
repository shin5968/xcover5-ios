/* M54: native CoreText framesetter wrapping with explicit-font run validation. */
#ifndef XC_PANEL_TEXTLAYOUT_H
#define XC_PANEL_TEXTLAYOUT_H
#include "panel-coretext.h"
static struct {
 __typeof__(&CTFramesetterCreateWithAttributedString) setter;
 __typeof__(&CTFramesetterCreateFrame) frame;
 __typeof__(&CTFrameGetVisibleStringRange) visible;
 __typeof__(&CTFrameGetLines) lines;
 __typeof__(&CTFrameGetLineOrigins) origins;
 __typeof__(&CTFrameDraw) draw;
 __typeof__(&CTLineGetTypographicBounds) bounds;
 __typeof__(&CTLineGetTrailingWhitespaceWidth) trailing;
 __typeof__(&CTLineGetGlyphRuns) runs;
 __typeof__(&CTRunGetAttributes) attributes;
 __typeof__(&CTRunGetGlyphCount) count;
 __typeof__(&CTRunGetGlyphs) glyphs;
 __typeof__(&CGPathCreateWithRect) path;
 __typeof__(&CGPathRelease) path_release;
 CFStringRef font_key,color_key;
} m54ct;
static int m54_load_layout(void) {
 if(m53_load_text())return 1;
 fprintf(stderr,"XCOVER5 M54 PHASE resolve_framesetter\n");
 void *ct=dlopen("/System/Library/Frameworks/CoreText.framework/CoreText",RTLD_NOW|RTLD_LOCAL);
 void *cg=dlopen("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",RTLD_NOW|RTLD_LOCAL);
 if(!ct || !cg)return 2;
#define M54_RESOLVE(h,field,symbol) do{dlerror();void *p=dlsym(h,symbol);const char *e=dlerror();if(e || !p){fprintf(stderr,"M54 symbol=%s error=%s\n",symbol,e?e:"null");return 3;}memcpy(&m54ct.field,&p,sizeof p);}while(0)
 M54_RESOLVE(ct,setter,"CTFramesetterCreateWithAttributedString");M54_RESOLVE(ct,frame,"CTFramesetterCreateFrame");
 M54_RESOLVE(ct,visible,"CTFrameGetVisibleStringRange");M54_RESOLVE(ct,lines,"CTFrameGetLines");
 M54_RESOLVE(ct,origins,"CTFrameGetLineOrigins");M54_RESOLVE(ct,draw,"CTFrameDraw");
 M54_RESOLVE(ct,bounds,"CTLineGetTypographicBounds");M54_RESOLVE(ct,trailing,"CTLineGetTrailingWhitespaceWidth");
 M54_RESOLVE(ct,runs,"CTLineGetGlyphRuns");M54_RESOLVE(ct,attributes,"CTRunGetAttributes");
 M54_RESOLVE(ct,count,"CTRunGetGlyphCount");M54_RESOLVE(ct,glyphs,"CTRunGetGlyphs");
 M54_RESOLVE(cg,path,"CGPathCreateWithRect");M54_RESOLVE(cg,path_release,"CGPathRelease");
 /* dlsym addresses the exported CFStringRef variable, not the string object. */
 M54_RESOLVE(ct,font_key,"kCTFontAttributeName");M54_RESOLVE(ct,color_key,"kCTForegroundColorFromContextAttributeName");
#undef M54_RESOLVE
 if(!m54ct.font_key || !m54ct.color_key)return 4;
 puts("XCOVER5 M54 RESOLVE PASS:14 SDK-typed functions and2 attribute constants");return 0;
}
static int m54_paragraph(CGContextRef c,CTFontRef font,const char *text,double width,double height,unsigned *line_count) {
 size_t n=strlen(text);*line_count=0;
 if(!n || n>512 || !isfinite(width) || !isfinite(height) || width<1 || width>510 || height<1 || height>500)return 1;
 for(size_t i=0;i<n;i++)if(text[i]!=' ' && (text[i]<'A' || text[i]>'Z'))return 1;
 int rc=2;CFStringRef string=CFStringCreateWithCString(NULL,text,kCFStringEncodingASCII);
 CFDictionaryRef attrs=NULL;CFAttributedStringRef attributed=NULL;CTFramesetterRef setter=NULL;CTFrameRef frame=NULL;CGPathRef path=NULL;
 if(!string)goto done;
 const void *keys[]={m54ct.font_key,m54ct.color_key},*values[]={font,kCFBooleanTrue};
 attrs=CFDictionaryCreate(NULL,keys,values,2,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);if(!attrs)goto done;
 attributed=CFAttributedStringCreate(NULL,string,attrs);if(!attributed)goto done;
 setter=m54ct.setter(attributed);if(!setter)goto done;
 path=m54ct.path((CGRect){{110,360},{width,height}},NULL);if(!path)goto done;
 frame=m54ct.frame(setter,CFRangeMake(0,0),path,NULL);if(!frame)goto done;
 CFRange visible=m54ct.visible(frame);rc=3;
 if(visible.location!=0 || visible.length!=(CFIndex)n)goto done;
 CFArrayRef lines=m54ct.lines(frame);CFIndex count=lines?CFArrayGetCount(lines):0;
 if(count<1 || count>24)goto done;
 CGPoint origins[24];m54ct.origins(frame,CFRangeMake(0,count),origins);rc=4;
 for(CFIndex i=0;i<count;i++) {
  CTLineRef line=(CTLineRef)CFArrayGetValueAtIndex(lines,i);
  double used=m54ct.bounds(line,NULL,NULL,NULL)-m54ct.trailing(line);
  if(!isfinite(used) || used<0 || used>width+1 || !isfinite(origins[i].x) || !isfinite(origins[i].y) ||
     origins[i].x<0 || origins[i].x>width || origins[i].y<0 || origins[i].y>height || (i && origins[i].y>=origins[i-1].y))goto done;
  CFArrayRef runs=m54ct.runs(line);CFIndex run_count=runs?CFArrayGetCount(runs):0;if(run_count<1)goto done;
  for(CFIndex j=0;j<run_count;j++) {
   CTRunRef run=(CTRunRef)CFArrayGetValueAtIndex(runs,j);CFDictionaryRef a=m54ct.attributes(run);if(!a)goto done;
   CTFontRef actual=(CTFontRef)CFDictionaryGetValue(a,m54ct.font_key);if(!actual)goto done;
   CFStringRef name=m53ct.name(actual);int identity=name && CFStringCompare(name,CFSTR("XCoverPanelTest-Regular"),0)==kCFCompareEqualTo;
   if(name)CFRelease(name);if(!identity)goto done;
   CFIndex glyph_count=m54ct.count(run);if(glyph_count<1 || glyph_count>512)goto done;
   CGGlyph glyphs[512];m54ct.glyphs(run,CFRangeMake(0,glyph_count),glyphs);
   for(CFIndex k=0;k<glyph_count;k++)if(!glyphs[k])goto done;
  }
 }
 m54ct.draw(frame,c);*line_count=(unsigned)count;rc=0;
done:
 if(frame)CFRelease(frame);if(path)m54ct.path_release(path);if(setter)CFRelease(setter);
 if(attributed)CFRelease(attributed);if(attrs)CFRelease(attrs);if(string)CFRelease(string);return rc;
}
static int m54_draw(uint32_t *p,unsigned frame) {
 if(m53_draw(p,frame))return 1;
 fprintf(stderr,"XCOVER5 M54 PHASE attributed_paragraph frame=%u\n",frame+1);
 CGDataProviderRef provider=m53ct.provider(NULL,m53_font_bytes,sizeof m53_font_bytes,NULL);if(!provider)return 2;
 CGFontRef graphics=m53ct.font(provider);m53ct.provider_release(provider);if(!graphics)return 2;
 CTFontRef font=m53ct.ctfont(graphics,28,NULL,NULL),title=m53ct.ctfont(graphics,44,NULL,NULL);m53ct.font_release(graphics);
 if(!font || !title){if(font)CFRelease(font);if(title)CFRelease(title);return 2;}
 CGColorSpaceRef space=m52cg.space();if(!space){CFRelease(font);CFRelease(title);return 2;}
 CGContextRef c=m52cg.create(p,720,1480,8,2880,space,kCGImageAlphaPremultipliedFirst|kCGBitmapByteOrder32Little);m52cg.space_release(space);
 if(!c){CFRelease(font);CFRelease(title);return 2;}
 if(m52cg.data(c)!=p){m52cg.release(c);CFRelease(font);CFRelease(title);return 2;}
 m52_fill(c,40,1280,640,80,0.18,0.48,0.72);m52_fill(c,92,340,536,540,0.06,0.12,0.2);
 m53ct.matrix(c,(CGAffineTransform){1,0,0,1,0,0});m53ct.mode(c,kCGTextFill);m52cg.fill_color(c,1,1,1,1);
 int rc=m53_line(c,title,"TEXT LAYOUT M54",70,1300);unsigned before=m53_white(p),lines=0;
 double width=360+(frame%4)*50;
 fprintf(stderr,"XCOVER5 M54 PHASE framesetter_draw frame=%u width=%.0f\n",frame+1,width);
 if(!rc)rc=m54_paragraph(c,font,"CORETEXT WRAPS THIS PARAGRAPH INTO LINES USING AN EXPLICIT FONT AND THE AVAILABLE WIDTH EACH FRAME USES THE SAME TEXT WITH A DIFFERENT COLUMN WIDTH ALL CHARACTERS MUST FIT INSIDE THE FRAME AND EVERY GLYPH RUN MUST KEEP THE SUPPLIED FONT",width,500,&lines);
 m52cg.flush(c);m52cg.release(c);CFRelease(font);CFRelease(title);if(rc || lines<4)return 3;
 unsigned after=m53_white(p);if(after<before+1000)return 4;
 for(unsigned y=0;y<1480;y++)if(p[y*720]!=0xffff0000U || p[y*720+719]!=0xff0000ffU)return 5;
 for(unsigned i=0;i<720U*1480U;i++)if((p[i]>>24)!=255)return 6;
 printf("XCOVER5 M54 LAYOUT PASS frame=%u lines=%u width=%.0f visible_all=1 font_runs=1 new_pixels=%u\n",frame+1,lines,width,after-before);return 0;
}
#endif
