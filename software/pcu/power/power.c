#include "hal.h"
#include "power.h"
#include "measurement.h"
#include "docking.h"
#include "debug.h"

pcu_returncode_e power5v(void) {
    debug_log("[I] powering 5v\n");
    palClearLine(LINE_DISABLE_LM2596);
    return pcuSUCCESS;
}

pcu_returncode_e unpower5v(void) {
    debug_log("[I] unpowering 5v\n");
    palSetLine(LINE_DISABLE_LM2596);
    return pcuSUCCESS;
}

pcu_returncode_e powerHdd(void) {
    debug_log("[I] powering HDD\n");
    palSetLine(LINE_SW_HDD_ON);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_ON);
    measurementValues_t values;
    measurement_getValues(&values);
    if (getDockingState() == pcu_dockingState3_allDockedPwrOn) {
        return pcuSUCCESS;
    }
    else {
        return pcuFAIL;
    }
}

pcu_returncode_e unpowerHdd(void) {
    debug_log("[I] unpowering HDD\n");
    palSetLine(LINE_SW_HDD_OFF);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_OFF);
    measurementValues_t values;
    measurement_getValues(&values);
    return pcuSUCCESS;
}

pcu_returncode_e powerBcu(void) {
    debug_log("[I] powering BCU\n");
    palSetLine(LINE_SW_SBC_ON);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_SBC_ON);
    return pcuSUCCESS;
}

pcu_returncode_e unpowerBcu(void) {
    debug_log("[I] unpowering BCU\n");
    palSetLine(LINE_SW_SBC_OFF);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_SBC_OFF);
    return pcuSUCCESS;
}
