#include "hal.h"
#include "chprintf.h"

void alarmClock_init(void) {
    rtcInit();
}

void alarmClock_getDate(char* buffer) {
    RTCDateTime timespec;
    rtcGetTime(&RTCD1, &timespec);
    chsnprintf(buffer, 61, "%02d:%02d:%02d:%03d - %02d-%02d-%04d",
               timespec.millisecond / 3600000U,
               (timespec.millisecond % 3600000U) / 60000U,
               (timespec.millisecond % 60000U) / 1000U,
               timespec.millisecond % 1000U,
               timespec.month,
               timespec.day,
               timespec.year + 1980U);
}
