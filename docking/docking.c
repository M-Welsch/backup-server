#include "docking.h"
#include "hal.h"
#include "measurement.h"
#include "bcuCommunication.h"
#include "chprintf.h"

static pcu_dockingstate_e dockingState = pcu_dockingState1_undocked;
static float currentLog[CURRENT_LOG_BUFFER_SIZE + 1];

static void pwmpcb(PWMDriver *pwmp) {
    (void)pwmp;
}


static PWMConfig motorPwmCfg = {
    100000,
    1000,
    pwmpcb,
    {
        {PWM_OUTPUT_ACTIVE_HIGH, NULL},
        {PWM_OUTPUT_DISABLED, NULL},
        {PWM_OUTPUT_DISABLED, NULL},
        {PWM_OUTPUT_DISABLED, NULL},
        },
    0,
    0,
    0
};

static inline void _motorDocking(void) {
#ifdef DOCKING_USE_PWM
    pwmcnt_t dutycycle = (pwmcnt_t) 5000;
#else
    pwmcnt_t dutycycle = (pwmcnt_t) 10000;
#endif
    pwmEnableChannel(&PWMD1, 0, PWM_PERCENTAGE_TO_WIDTH(&PWMD1, dutycycle));

    palClearLine(LINE_MOTOR_DRV2);
}

static inline void _motorUndocking(void) {
#ifdef DOCKING_USE_PWM
    pwmcnt_t dutycycle = (pwmcnt_t) 5000;
#else
    pwmcnt_t dutycycle = (pwmcnt_t) 0;
#endif
    pwmEnableChannel(&PWMD1, 0, PWM_PERCENTAGE_TO_WIDTH(&PWMD1, dutycycle));
    palSetLine(LINE_MOTOR_DRV2);
}


/**
 * @details (0,0) leads to high-Z, (1,1) leads to break. See Datasheet (DRV8220) p.11 Table 8.3
 */
static inline void _motorBreak(void) {
    pwmEnableChannel(&PWMD1, 0, PWM_PERCENTAGE_TO_WIDTH(&PWMD1, (pwmcnt_t) 10000));
    palSetLine(LINE_MOTOR_DRV2);
}

pcu_returncode_e dockingInit(void) {
    pwmStart(&PWMD1, &motorPwmCfg);
    pwmEnablePeriodicNotification(&PWMD1);
    _motorBreak();
    return pcuSUCCESS;
}

static inline bool _motorOvercurrent(uint16_t motor_current_measurement_value) {
    return motor_current_measurement_value > 250;
}

static inline pcu_dockingstate_e _dockingState(uint16_t sense) {
    if (sense > 3300) {
        if (measurement_getEndswitch() == PRESSED) {
            return pcu_dockingState1_undocked;
        }
        else {
            return pcu_dockingState9_inbetween;
        }
    }
    else if (sense > 3000) {
        return pcu_dockingState3_allDockedPwrOn;
    }
    else if (sense > 2500) {
        return pcu_dockingState4_allDocked12vOn;
    }
    else if (sense > 1700) {
        return pcu_dockingState5_allDocked5vOn;
    }
    else if (sense < 1100) {
        return pcu_dockingState2_allDockedPwrOff;
    }
    else {
        return pcu_dockingState_unknown;
    }
}

static void _updateDockingState(float *currentValue) {
    measurementValues_t values;
    measurement_getValues(&values);
    if (currentValue != NULL) {
        *currentValue = values.stator_supply_sense;
    }
    dockingState = _dockingState(values.stator_supply_sense);
}


static void _clearCurrentLog(void) {
    for (uint16_t ptr = 0; ptr < CURRENT_LOG_BUFFER_SIZE; ptr++) {
        currentLog[ptr] = 0.0f;
    }
}

uint16_t getFromCurrentLog(const uint16_t ptr) {
    return currentLog[ptr];
}


pcu_returncode_e dock(void) {
    _clearCurrentLog();
    _motorDocking();
    pcu_returncode_e retval = pcuSUCCESS;
    uint16_t countdown = MAXIMUM_DOCKING_TIME_1MS_TICKS;
    uint16_t counter = 0;
    while (countdown) {
        if (measurement_getDocked()) {
            /* needs to push in a little deeper. 50ms delay pushes the connector fully into its mating part */
            chThdSleepMilliseconds(40);
            break;
        }
        counter = MAXIMUM_DOCKING_TIME_1MS_TICKS - countdown;
        measurementValues_t values;
        measurement_getValues(&values);
        // currentLog[counter] = values.imotor_prot;
        static uint16_t overcurrent_count = 0;
        if (_motorOvercurrent(values.imotor_prot) && (counter > MAXIMUM_OVERCURRENT_INRUSH_SAMPLES)) {
            overcurrent_count++;
            if (overcurrent_count > MAXIMUM_CONSECUTIVE_OVERCURRENT_SAMPLES) {
                retval = pcuOVERCURRENT;
                break;
            }
        }
        else {
            overcurrent_count = 0;
        }
        chThdSleepMilliseconds(1);
        countdown--;
    }
    _motorBreak();
    if (!countdown) {
        return pcuTIMEOUT;
    }
    return retval;
}

pcu_returncode_e undock(void) {
    _clearCurrentLog();
    _motorUndocking();
    pcu_returncode_e retval = pcuSUCCESS;
    uint16_t countdown = MAXIMUM_DOCKING_TIME_1MS_TICKS;
    uint16_t counter = 0;
    while (countdown) {
        if (measurement_getEndswitch() == PRESSED) {
            break;
        }
        counter = MAXIMUM_DOCKING_TIME_1MS_TICKS - countdown;
        measurementValues_t values;
        measurement_getValues(&values);
        // currentLog[counter] = values.imotor_prot;
        static uint16_t overcurrent_count = 0;
        if (_motorOvercurrent(values.imotor_prot) && (counter > MAXIMUM_OVERCURRENT_INRUSH_SAMPLES)) {
            overcurrent_count++;
            if (overcurrent_count > MAXIMUM_CONSECUTIVE_OVERCURRENT_SAMPLES) {
                retval = pcuOVERCURRENT;
                break;
            }
        }
        else {
            overcurrent_count = 0;
        }
        chThdSleepMilliseconds(1);
        countdown--;
    }
    _motorBreak();
    if (!countdown) {
        return pcuTIMEOUT;
    }
    return retval;
}

pcu_returncode_e undock_(void) {
    _motorUndocking();
    while (measurement_getEndswitch() == NOT_PRESSED) {
        ;
    }
    _motorBreak();
    return pcuSUCCESS;
}

pcu_returncode_e powerHdd(void) {
    palSetLine(LINE_SW_HDD_ON);
    chThdSleepMilliseconds(100);
    palClearLine(LINE_SW_HDD_ON);
    measurementValues_t values;
    measurement_getValues(&values);
    dockingState = _dockingState(values.stator_supply_sense);
    if (dockingState == pcu_dockingState3_allDockedPwrOn) {
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

pcu_dockingstate_e getDockingState(void) {
    _updateDockingState(NULL);
    return dockingState;
}
