/* Observe the real CF date formatter. Never call SetFormat on a NULL result. */
#include <CoreFoundation/CoreFoundation.h>
#include <string.h>
static void m66_icu_probe(void) {
 struct stat st; errno=0;
 int rc=stat("/usr/share/icu/icudt70l.dat",&st), error=errno;
 printf("XCOVER5 M66 ICU stat=%d errno=%d bytes=%lld expected=30447056\n",rc,error,rc?-1LL:(long long)st.st_size);
 CFLocaleRef locale=CFLocaleCreate(kCFAllocatorDefault,CFSTR("en_US_POSIX"));
 CFDateFormatterRef formatter=CFDateFormatterCreate(kCFAllocatorDefault,locale,kCFDateFormatterShortStyle,kCFDateFormatterShortStyle);
 printf("XCOVER5 M66 DATE create=%d locale=%d\n",formatter!=NULL,locale!=NULL);
 if(formatter) {
  CFTimeZoneRef zone=CFTimeZoneCreateWithTimeIntervalFromGMT(kCFAllocatorDefault,0);
  if(zone)CFDateFormatterSetProperty(formatter,kCFDateFormatterTimeZone,zone);
  CFDateFormatterSetFormat(formatter,CFSTR("yyyy-MM-dd HH:mm:ss"));
  CFStringRef date=CFDateFormatterCreateStringWithAbsoluteTime(kCFAllocatorDefault,formatter,0);
  char text[80]={0};
  int converted=date && CFStringGetCString(date,text,sizeof(text),kCFStringEncodingUTF8);
  printf("XCOVER5 M66 DATE text=%s expected=2001-01-01_00:00:00 pass=%d; not UI readiness\n",converted?text:"<failed>",converted && strcmp(text,"2001-01-01 00:00:00")==0);
  if(date)CFRelease(date);
  if(zone)CFRelease(zone);
  CFRelease(formatter);
 }
 if(locale)CFRelease(locale);
}
