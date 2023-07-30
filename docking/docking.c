#include "docking.h"
#include "hal.h"
#include "measurement.h"

static inline void _motorDocking(void) {
    palSetLine(MOTOR_DRV1);
    palClearLine(MOTOR_DRV2);
}

static inline void _motorUndocking(void) {
    palClearLine(MOTOR_DRV1);
    palSetLine(MOTOR_DRV2);
}

static inline void _motorBreak(void) {
    palClearLine(MOTOR_DRV1);
    palClearLine(MOTOR_DRV2);
}

static inline bool _motorOvercurrent(uint16_t motor_current_measurement_value) {
    return motor_current_measurement_value > 100;
}

static inline pcu_returncode_e _dockingState(uint16_t sense) {
    // implement
    return pcu_dockingState2_allDockedPwrOff;
}

pcu_returncode_e dock(void) {
    _motorDocking();
    measurementValues_t values;
    pcu_returncode_e retval = pcuFAIL;
    pcu_returncode_e dockingState = pcu_dockingState1_Undocked;
    while (true) {  // check for timeout here
        measurement_getValues(&values);
        if (_motorOvercurrent(values.imotor_prot)) {
            break;
        }
        dockingState = _dockingState(values.stator_supply_sense);
        if (dockingState != pcu_dockingState1_Undocked) {
            break;
        }
    }
    _motorBreak();

    if (dockingState == pcu_dockingState2_allDockedPwrOff) {
        retval = pcuSUCCESS;
    }
    else {
        retval = dockingState;
    }

    return retval;
}

pcu_returncode_e undock(void) {
    return pcuFAIL;
}

pcu_returncode_e powerHdd(void) {
    palSetLine(LINE_SW_HDD_ON);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_ON);
    measurementValues_t values;
    measurement_getValues(&values);
    return _dockingState(values.stator_supply_sense);
}

pcu_returncode_e unpowerHdd(void) {
    palSetLine(LINE_SW_HDD_OFF);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_OFF);
    measurementValues_t values;
    measurement_getValues(&values);
    return _dockingState(values.stator_supply_sense);
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

