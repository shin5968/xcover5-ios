/* Bring-up identity pin for the locally verified iOS16.5 notifyd only.
 * Not a trust-cache implementation; signature parsing/page checks remain active. */
static inline int
xcover5_notify_platform(const unsigned char *cdhash, unsigned int cs_flags,
    unsigned int platform)
{
    static const unsigned char expected[20] = {
        0xd2,0x93,0xd8,0x5f,0xdc,0xc8,0x5b,0x78,0x21,0x4c,
        0x0e,0x0b,0xc0,0x13,0x94,0x5f,0x1a,0xe2,0xca,0x05
    };
    if (cdhash == 0 || platform != 2 || !(cs_flags & 2)) { return 0; }
    for (unsigned int i = 0; i < sizeof(expected); i++) {
        if (cdhash[i] != expected[i]) { return 0; }
    }
    return 1;
}
