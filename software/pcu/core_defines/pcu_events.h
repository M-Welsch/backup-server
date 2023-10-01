//
// Created by max on 27.09.23.
//

#ifndef BASE_PCU_PCU_EVENTS_H
#define BASE_PCU_PCU_EVENTS_H

#include "chevents.h"

#define EVENT_SHUTDOWN_REQUESTED                EVENT_MASK(0)
#define EVENT_SHUTDOWN_ABORTED                  EVENT_MASK(1)
#define EVENT_WAKEUP_REQUESTED_BY_ALARMCLOCK    EVENT_MASK(2)
#define EVENT_WAKEUP_REQUESTED_BY_USER          EVENT_MASK(3)
#define EVENT_BUTTON_0_PRESSED                  EVENT_MASK(4)
#define EVENT_BUTTON_1_PRESSED                  EVENT_MASK(5)

#endif //BASE_PCU_PCU_EVENTS_H
