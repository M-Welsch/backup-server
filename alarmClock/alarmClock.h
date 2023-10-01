//
// Created by max on 19.07.23.
//

#ifndef BASE_PCU_ALARM_CLOCK_H
#define BASE_PCU_ALARM_CLOCK_H

#include "core_defines.h"

void alarmClock_init(void);

pcu_returncode_e alarmClock_argsToRtcDateTime(RTCDateTime* timespec, int argc, char *argv[]);
pcu_returncode_e alarmClock_RtcDateTimeToStr(char* outstr, const RTCDateTime* timespec);

pcu_returncode_e alarmClock_setDateNow(const RTCDateTime* timespec);
pcu_returncode_e alarmClock_getDateNow(RTCDateTime* timespec);
pcu_returncode_e alarmClock_setDateWakeup(RTCDateTime* timespec);
pcu_returncode_e alarmClock_getDateWakeup(RTCDateTime* timespec);

pcu_returncode_e alarmClock_setDateBackup(const RTCDateTime* timespec);
pcu_returncode_e alarmClock_getDateBackup(RTCDateTime* timespec);


#endif //BASE_PCU_ALARM_CLOCK_H
