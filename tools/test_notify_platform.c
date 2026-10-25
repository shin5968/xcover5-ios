#include <assert.h>
#include <stdio.h>
#include "xcover5_notify_platform.h"
int main(void) {
    unsigned char h[20]={0xd2,0x93,0xd8,0x5f,0xdc,0xc8,0x5b,0x78,0x21,0x4c,0x0e,0x0b,0xc0,0x13,0x94,0x5f,0x1a,0xe2,0xca,0x05};
    assert(xcover5_notify_platform(h,2,2));
    assert(!xcover5_notify_platform(0,2,2));
    assert(!xcover5_notify_platform(h,0,2));
    assert(!xcover5_notify_platform(h,2,1));
    for(unsigned int i=0;i<20;i++) {
        h[i]^=1;assert(!xcover5_notify_platform(h,2,2));h[i]^=1;
    }
    puts("notifyd identity pin: exact hash/ad-hoc/iOS and 20 mutated-byte rejections PASS");
}
