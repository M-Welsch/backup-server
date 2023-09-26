//
// Created by max on 22.09.23.
//

#ifndef BASE_PCU_STATEMACHINE_H
#define BASE_PCU_STATEMACHINE_H

#include "ch.h"

typedef enum {
  STATE_ACTIVE,
  STATE_SHUTDOWN_REQUESTED,
  STATE_DEEP_SLEEP,
  STATE_HMI
} state_codes_e;

void statemachine_mainloop(void);
void statemachine_init(void);
void statemachine_sendEvent(eventmask_t event);

#endif //BASE_PCU_STATEMACHINE_H
