//
// Created by max on 22.09.23.
//

#ifndef BASE_PCU_STATEMACHINE_H
#define BASE_PCU_STATEMACHINE_H

typedef enum {
  STATE_ACTIVE,
  STATE_SHUTDOWN_REQUESTED,
  STATE_DEEP_SLEEP,
  STATE_HMI
} state_codes_e;

#endif //BASE_PCU_STATEMACHINE_H
