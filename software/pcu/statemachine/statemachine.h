//
// Created by max on 22.09.23.
//

#ifndef BASE_PCU_STATEMACHINE_H
#define BASE_PCU_STATEMACHINE_H

#define DEFAULT_MILLISECONDS_TO_SHUTDOWN 5000
#define MAXIMUM_MILLISECONDS_TO_SHUTDOWN 60000

#include "ch.h"

typedef enum {
  STATE_INIT,
  STATE_ACTIVE,
  STATE_SHUTDOWN_REQUESTED,
  STATE_DEEP_SLEEP,
  STATE_HMI
} state_codes_e;

typedef enum {
  WAKEUP_REASON_POWER_ON,
  WAKEUP_REASON_USER_REQUEST,
  WAKEUP_REASON_SCHEDULED
} wakeup_reason_e;

wakeup_reason_e statemachine_getWakeupReason(void);
void statemachine_mainloop(void);
void statemachine_init(void);
void statemachine_sendEvent(eventmask_t event);
void statemachine_sendEventFromIsr(eventmask_t event);
void statemachine_setMillisecondsToShutdown(uint32_t milliseconds);
state_codes_e statemachine_getCurrentState(void);

#endif //BASE_PCU_STATEMACHINE_H
