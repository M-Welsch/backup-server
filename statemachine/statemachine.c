#include "stdint-gcc.h"

#include "statemachine.h"
#include "ch.h"

int STATE_ACTIVE_state(void) {
    return STATE_SHUTDOWN_REQUESTED;
}

int STATE_SHUTDOWN_REQUESTED_state(void) {
    return STATE_DEEP_SLEEP;
}

int STATE_DEEP_SLEEP_state(void) {
    return STATE_HMI;
}

int STATE_HMI_state(void) {
    return STATE_ACTIVE;
}

/* array and enum must be in sync! */
int (* state[])(void) = {
    STATE_ACTIVE_state,
    STATE_SHUTDOWN_REQUESTED_state,
    STATE_DEEP_SLEEP_state,
    STATE_HMI_state
};


struct transition {
    state_codes_e src_state;
    state_codes_e dst_state;
};
struct transition state_transitions[] = {
        {STATE_ACTIVE, STATE_SHUTDOWN_REQUESTED},
        {STATE_SHUTDOWN_REQUESTED,   STATE_ACTIVE},
        {STATE_SHUTDOWN_REQUESTED,   STATE_DEEP_SLEEP},
        {STATE_DEEP_SLEEP,   STATE_ACTIVE},
        {STATE_DEEP_SLEEP,   STATE_HMI},
        {STATE_HMI,   STATE_DEEP_SLEEP},
        {STATE_HMI,   STATE_ACTIVE}};

#define EXIT_STATE STATE_DEEP_SLEEP
#define ENTRY_STATE STATE_ACTIVE

#define DIMENSION(x) (uint8_t)(sizeof(x)/sizeof(x[0]))

int lookup_transitions(state_codes_e cur_state, state_codes_e desired_state) {
    for (uint8_t i = 0; i < DIMENSION(state_transitions); i++) {
        struct transition current_transition = state_transitions[i];
        if ((current_transition.src_state == cur_state) && (current_transition.dst_state == desired_state)) {
            return desired_state;
        }
    }

    //chprintf(chp, "Log:E:Invalid State transition from %i to %i", cur_state, desired_state);
    return cur_state;
}

void random_function (void)  {
    state_codes_e cur_state = ENTRY_STATE;
    state_codes_e desired_state = ENTRY_STATE;
    int (* state_fun)(void);

    while (true) {
        state_fun = state[cur_state];
        desired_state = state_fun();
        if (EXIT_STATE == cur_state)
            break;
        cur_state = lookup_transitions(cur_state, desired_state);
        chThdSleepMilliseconds(200);
    }
}
