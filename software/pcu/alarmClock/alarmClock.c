#include <stdlib.h>
#include "hal.h"
#include "chprintf.h"
#include "alarmClock.h"
#include "bcuCommunication.h"
#include "statemachine.h"
#include "pcu_events.h"
#include "debug.h"

static RTCDateTime date_wakeup;
static RTCDateTime date_backup;

static void alarmcb(RTCDriver *rtcp, rtcevent_t event) {
    UNUSED_PARAM(rtcp);
    RTCDateTime timespec;
    rtcGetTime(&RTCD1, &timespec);
    if ((event == RTC_EVENT_ALARM_A) &&
        (date_wakeup.year == timespec.year) &&
        (date_wakeup.month == timespec.month))
    {
        statemachine_sendEventFromIsr(EVENT_WAKEUP_REQUESTED_BY_ALARMCLOCK);
    }
}

void alarmClock_init(void) {
    rtcInit();
    rtcSetCallback(&RTCD1, alarmcb);
}

pcu_returncode_e alarmClock_setDateNow(const RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    rtcSetTime(&RTCD1, timespec);
    char buffer[64];
    alarmClock_RtcDateTimeToStr(buffer, timespec);
    debug_log("[I] alarmclock setting now date to %s\n", buffer);
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
    date_wakeup = *timespec;
    uint32_t day = timespec->day;
    uint32_t hour = timespec->millisecond / 3600000U;
    uint32_t minute = (timespec->millisecond % 3600000U) / 60000U;
    RTCAlarm alarm1 = {
        RTC_ALRM_DT(day / 10) |
        RTC_ALRM_DU(day % 10) |
        RTC_ALRM_HT(hour / 10) |
        RTC_ALRM_HU(hour % 10) |
        RTC_ALRM_MNT(minute / 10) |
        RTC_ALRM_MNU(minute % 10) |
        RTC_ALRM_ST(0) |
        RTC_ALRM_SU(0)
    };

    rtcSetAlarm(&RTCD1, 0, &alarm1);
    char buffer[64];
    alarmClock_RtcDateTimeToStr(buffer, timespec);
    debug_log("[I] alarmclock setting wakeup date to %s\n", buffer);
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_getDateWakeup(RTCDateTime* timespec) {
    if (timespec == NULL) {
        return pcuFAIL;
    }
    RTCAlarm alarmspec;
    rtcGetAlarm(&RTCD1, 0, &alarmspec);
    uint32_t day_unit = (alarmspec.alrmr & RTC_ALRMAR_DU) >> RTC_ALRMAR_DU_Pos;
    uint32_t day_ten = (alarmspec.alrmr & RTC_ALRMAR_DT) >> RTC_ALRMAR_DT_Pos;
    uint32_t minute_ten = (alarmspec.alrmr & RTC_ALRMAR_MNT) >> RTC_ALRMAR_MNT_Pos;
    uint32_t minute_unit = (alarmspec.alrmr & RTC_ALRMAR_MNU) >> RTC_ALRMAR_MNU_Pos;
    uint32_t hour_ten = (alarmspec.alrmr & RTC_ALRMAR_HT) >> RTC_ALRMAR_HT_Pos;
    uint32_t hour_unit = (alarmspec.alrmr & RTC_ALRMAR_HU) >> RTC_ALRMAR_HU_Pos;
    timespec->day = 10 *day_ten + day_unit;
    timespec->millisecond = 1000*60*(10*minute_ten + minute_unit) + 1000*3600*(10*hour_ten + hour_unit);
    timespec->month = date_wakeup.month;
    timespec->year = date_wakeup.year;
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_setDateBackup(const RTCDateTime* timespec) {
    date_backup = *timespec;
    char buffer[64];
    alarmClock_RtcDateTimeToStr(buffer, timespec);
    debug_log("[I] alarmclock setting backup date to %s\n", buffer);
    return pcuSUCCESS;
}

pcu_returncode_e alarmClock_getDateBackup(RTCDateTime* timespec) {
    *timespec = date_backup;
    return pcuSUCCESS;
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
    chsnprintf(outstr, 61, "%02d:%02d:%02d - %02d-%02d-%04d",
               timespec->millisecond / 3600000U,
               (timespec->millisecond % 3600000U) / 60000U,
               (timespec->millisecond % 60000U) / 1000U,
               timespec->day,
               timespec->month,
               timespec->year + 1980U);
    return pcuSUCCESS;
}
