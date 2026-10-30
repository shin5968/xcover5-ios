/* M51 CPU scene renderer. All rectangles use clipped half-open coordinates. */
#ifndef XC_PANEL_SCENE_H
#define XC_PANEL_SCENE_H
#include <stdint.h>
#define M51_W 720
#define M51_H 1480
static void m51_rect(uint32_t *p,int x,int y,int w,int h,uint32_t color) {
 if(w<=0 || h<=0)return;
 /* Promote before addition so hostile/offscreen coordinates cannot overflow. */
 int64_t right=(int64_t)x+w,bottom=(int64_t)y+h;
 int left=x<0?0:x,top=y<0?0:y;
 if(right>M51_W)right=M51_W;if(bottom>M51_H)bottom=M51_H;
 for(int row=top;row<bottom;row++)for(int col=left;col<right;col++)p[row*M51_W+col]=color;
}
static void m51_scene(uint32_t *p,unsigned frame) {
 frame%=16;
 for(unsigned y=0;y<M51_H;y++)for(unsigned x=0;x<M51_W;x++)
  p[y*M51_W+x]=0xff000000U|((20+y/40)<<16)|((30+y/24)<<8)|(65+x/12);
 /* Status bar, battery, and desktop app tiles. */
 m51_rect(p,0,0,720,68,0xff101827U);
 for(int i=0;i<4;i++)m51_rect(p,28+i*14,40-i*6,8,8+i*6,0xffe4e9f2U);
 m51_rect(p,622,22,66,26,0xffe4e9f2U);m51_rect(p,626,26,50,18,0xff44cc88U);
 for(int i=0;i<4;i++){
  m51_rect(p,40+i*170,110,120,120,0xff304b73U+i*0x000b1808U);
  m51_rect(p,60+i*170,145,80,12,0xffdce8ffU);
  m51_rect(p,60+i*170,175,50,12,0xffdce8ffU);
 }
 /* Back window and its content. */
 m51_rect(p,44,314,586,664,0xff080d18U);
 m51_rect(p,36,302,586,664,0xffe7edf6U);
 m51_rect(p,36,302,586,58,0xff2563a8U);
 for(int i=0;i<7;i++)m51_rect(p,64,398+i*66,480-i*35,18,0xff879ab4U);
 /* Foreground window moves across and beyond the right screen edge. */
 int wx=150+(int)frame*22,wy=584+(int)(frame%4)*12;
 m51_rect(p,wx+8,wy+12,480,480,0xff080d18U);
 m51_rect(p,wx,wy,480,480,0xff18283fU);
 m51_rect(p,wx,wy,480,54,0xff9050c8U);
 for(int i=0;i<3;i++)m51_rect(p,wx+20+i*28,wy+18,14,14,0xffeeddf8U);
 for(int i=0;i<5;i++)m51_rect(p,wx+30+i*78,wy+360-(int)((frame+i*3)%12)*20,48,80+(int)((frame+i*3)%12)*20,0xff38bdb0U);
 /* Dock and progress overlay are composed last. */
 m51_rect(p,30,1298,660,126,0xff18283fU);
 for(int i=0;i<5;i++)m51_rect(p,60+i*126,1320,96,82,0xff406895U+i*0x00090c05U);
 m51_rect(p,36,1440,648,12,0xff101827U);
 m51_rect(p,36,1440,(int)(frame+1)*40,12,0xff38dfb4U);
}
#endif
