#include "hal.h"
#include "power.h"
#include "measurement.h"
#include "docking.h"


pcu_returncode_e power5v(void) {
    palClearLine(LINE_DISABLE_LM2596);
    return pcuSUCCESS;
}

pcu_returncode_e unpower5v(void) {
    palSetLine(LINE_DISABLE_LM2596);
    return pcuSUCCESS;
}

pcu_returncode_e powerHdd(void) {
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
    palSetLine(LINE_SW_HDD_OFF);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_OFF);
    measurementValues_t values;
    measurement_getValues(&values);
    return pcuSUCCESS;
}

pcu_returncode_e powerBcu(void) {
    palSetLine(LINE_SW_SBC_ON);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_SBC_ON);
    return pcuSUCCESS;
}

pcu_returncode_e unpowerBcu(void) {
    palSetLine(LINE_SW_SBC_OFF);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_SBC_OFF);
    return pcuSUCCESS;
}
