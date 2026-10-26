#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static unsigned long xc_enter(void){assert(!pthread_mutex_lock(&mutex));return 0;}
static void xc_leave(unsigned long state){(void)state;assert(!pthread_mutex_unlock(&mutex));}
#include "capture.h"
static void *writer(void *arg){for(unsigned i=0;i<10000;i++)xc_capture((unsigned char)(uintptr_t)arg);return NULL;}
int main(void){
 assert(sizeof(xc_meta)==40);
 assert(xc_crc32((const unsigned char *)"123456789",9)==0xcbf43926);
 assert(!xc_ack((const unsigned char *)&xc_meta,sizeof(xc_meta)));
 pthread_t workers[4];
 for(uintptr_t i=0;i<4;i++)assert(!pthread_create(workers+i,NULL,writer,(void*)(i+1)));
 for(unsigned i=0;i<4;i++)assert(!pthread_join(workers[i],NULL));
 assert(xc_meta.size==40000 && !xc_meta.ready && !xc_meta.dropped);
 unsigned counts[5]={0};for(unsigned i=0;i<xc_meta.size;i++){assert(xc_log[i]>=1&&xc_log[i]<=4);counts[xc_log[i]]++;}
 for(unsigned i=1;i<=4;i++)assert(counts[i]==10000);
 xc_finish(123,0x8e00);assert(xc_meta.ready && xc_meta.run==123 && xc_meta.status==0x8e00);
 uint32_t crc=xc_meta.crc;xc_capture(9);xc_finish(456,0);assert(xc_meta.size==40000 && xc_meta.crc==crc && xc_meta.run==123);
 unsigned char b[256];assert(xc_read_log(40001,b,256)==0);assert(xc_read_log(39999,b,256)==1);assert(xc_read_log(0,b,256)==256);
 struct xc_meta bad=xc_meta;bad.run++;assert(!xc_ack((const unsigned char *)&bad,sizeof(bad)));
 bad=xc_meta;bad.crc++;assert(!xc_ack((const unsigned char *)&bad,sizeof(bad)));
 assert(!xc_ack((const unsigned char *)&xc_meta,sizeof(xc_meta)-1));
 assert(xc_ack((const unsigned char *)&xc_meta,sizeof(xc_meta)) && xc_acknowledged);
 xc_frozen=xc_acknowledged=0;memset(&xc_meta,0,sizeof(xc_meta));
 for(unsigned i=0;i<XC_LOG_CAP+3;i++)xc_capture('a');
 assert(xc_meta.size==XC_LOG_CAP && xc_meta.dropped==3);xc_finish(789,0);
 assert(!xc_ack((const unsigned char *)&xc_meta,sizeof(xc_meta)) && !xc_acknowledged);
 puts("AUTO capture: concurrent publication, immutable snapshot, CRC, bounds, stale ACK, overflow reset gate PASS (host only)");
}
