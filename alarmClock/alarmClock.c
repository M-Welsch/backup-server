#include <stdlib.h>
#include "hal.h"
#include "chprintf.h"
#include "alarmClock.h"

void alarmClock_init(void) {
    rtcInit();
}

pcu_returncode_e alarmClock_setDateNow(const RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    rtcSetTime(&RTCD1, timespec);
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_getDateNow(RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    rtcGetTime(&RTCD1, timespec);
    return pcuSUCCESS;
}

/**
 * @note see RM0360 p.513, section 21.7.7 for reference
 * @param timespec
 * @return
 */
pcu_returncode_e alarmClock_setDateWakeup(RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    rtcGetTime(&RTCD1, timespec);
    uint32_t day = timespec->day;
    uint32_t hour = timespec->millisecond / 3600000U;  // not sure
    uint32_t minute = (timespec->millisecond % 3600000U) / 60000U;
    RTCAlarm alarm1 = {
        RTC_ALRM_DU(day) |
        RTC_ALRM_HU(hour) |
        RTC_ALRM_MNT(minute / 10) |
        RTC_ALRM_MNU(minute % 10) |
        RTC_ALRM_ST(0) |
        RTC_ALRM_SU(0)
    };

    rtcSetAlarm(&RTCD1, 0, &alarm1);
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_getDateWakeup(RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    rtcGetTime(&RTCD1, timespec);
    RTCAlarm alarmspec;
    rtcGetAlarm(&RTCD1, 0, &alarmspec);
    return pcuSUCCESS;
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

pcu_returncode_e alarmClock_argsToRtcDateTime(RTCDateTime* timespec, int argc, char *argv[]) {
    if (argc < 5) {
        return pcuFAIL;
    }
    char *endPtr;
    uint32_t year = strtol(argv[0], &endPtr, 10) - 1980;
    uint32_t month = strtol(argv[1], &endPtr, 10);
    uint32_t day = strtol(argv[2], &endPtr, 10);
    uint32_t hour = strtol(argv[3], &endPtr, 10);
    uint32_t minute = strtol(argv[4], &endPtr, 10);

    if (month > 12 || day > 31 || hour > 24 || minute > 60) {
        return pcuFAIL;
    }
    timespec->year = year;
    timespec->month = month;
    timespec->day = day;
    timespec->millisecond = 1000 * (hour*3600 + minute*60);
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_RtcDateTimeToStr(char* outstr, const RTCDateTime* timespec) {
    if (outstr == NULL || timespec == NULL) {
        return pcuFAIL;
    }
    chsnprintf(outstr, 61, "%02d:%02d:%02d:%03d - %02d-%02d-%04d",
               timespec->millisecond / 3600000U,
               (timespec->millisecond % 3600000U) / 60000U,
               (timespec->millisecond % 60000U) / 1000U,
               timespec->millisecond % 1000U,
               timespec->month,
               timespec->day,
               timespec->year + 1980U);
    return pcuSUCCESS;
}
