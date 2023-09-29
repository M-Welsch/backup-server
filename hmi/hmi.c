#include "hal.h"

#include "hmi.h"
#include "core_defines.h"
#include "statemachine.h"
#include "pcu_events.h"

static void pb0_cb(void *arg) {
    UNUSED_PARAM(arg);
    statemachine_sendEventFromIsr(EVENT_BUTTON_0_PRESSED);
}

static void pb1_cb(void *arg) {
    UNUSED_PARAM(arg);
    statemachine_sendEventFromIsr(EVENT_BUTTON_1_PRESSED);
}

void hmi_init(void) {
    palEnableLineEvent(LINE_HMI_PUSHUBUTTON_0, PAL_EVENT_MODE_FALLING_EDGE);
    palSetLineCallback(LINE_HMI_PUSHUBUTTON_0, pb0_cb, NULL);

    palEnableLineEvent(LINE_HMI_PUSHUBUTTON_1, PAL_EVENT_MODE_FALLING_EDGE);
    palSetLineCallback(LINE_HMI_PUSHUBUTTON_1, pb1_cb, NULL);
}
