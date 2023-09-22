/*
    ChibiOS - Copyright (C) 2006..2018 Giovanni Di Sirio

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/

#include "ch.h"
#include "hal.h"
#include "rt_test_root.h"
#include "oslib_test_root.h"
#include "bcuCommunication.h"
#include "alarmClock.h"
#include "chprintf.h"
#include "measurement.h"
#include "docking.h"


//
//typedef enum
//{
//    stFAIL = 0,     /**< Error, operation fail */
//    stSUCCESS = 1   /**< Operation success*/
//} returnCode_e;
//
//typedef enum { running, sleepy, standby, hmi} state_codes_e;
//
//int running_state(BaseSequentialStream* chp) {
//    chprintf(chp, "running_state");
//    return sleepy;
//}
//
//int sleepy_state(BaseSequentialStream* chp) {
//    chprintf(chp, "sleepy_state");
//    return standby;
//}
//
//int standby_state(BaseSequentialStream* chp) {
//    chprintf(chp, "standby_state");
//    return hmi;
//}
//
//int hmi_state(BaseSequentialStream* chp) {
//    chprintf(chp, "hmi_state");
//    return running;
//}
//
//
///* array and enum below must be in sync! */
//int (* state[])(BaseSequentialStream*) = { running_state, sleepy_state, standby_state, hmi_state};
//
//
//struct transition {
//    state_codes_e src_state;
//    state_codes_e dst_state;
//};
//struct transition state_transitions[] = {
//        {running, sleepy},
//        {sleepy,   running},
//        {sleepy,   standby},
//        {standby,   running},
//        {standby,   hmi},
//        {hmi,   standby},
//        {hmi,   running}};
//
//#define EXIT_STATE standby
//#define ENTRY_STATE running
//
//#define DIMENSION(x) (uint8_t)(sizeof(x)/sizeof(x[0]))
//
//int lookup_transitions(state_codes_e cur_state, state_codes_e desired_state) {
//    for (uint8_t i = 0; i < DIMENSION(state_transitions); i++) {
//        struct transition current_transition = state_transitions[i];
//        if ((current_transition.src_state == cur_state) && (current_transition.dst_state == desired_state)) {
//            return desired_state;
//        }
//    }
//
//    BaseSequentialStream *chp = (BaseSequentialStream*) &SDU1;
//    chprintf(chp, "Log:E:Invalid State transition from %i to %i", cur_state, desired_state);
//    return cur_state;
//}
//
//
//static THD_WORKING_AREA(statemachineThread, 128);
//static THD_FUNCTION(Statemachine, arg) {
//    (void)arg;
//    BaseSequentialStream *chp = (BaseSequentialStream*) &SDU1;
//
//    state_codes_e cur_state = ENTRY_STATE;
//    state_codes_e desired_state = ENTRY_STATE;
//    int (* state_fun)(BaseSequentialStream*);
//
//    while (true) {
//        state_fun = state[cur_state];
//        desired_state = state_fun(chp);
//        if (EXIT_STATE == cur_state)
//            break;
//        cur_state = lookup_transitions(cur_state, desired_state);
//        chThdSleepMilliseconds(200);
//    }
//}




int main(void) {
    halInit();
    dockingInit();

    palClearPad(GPIOB, GPIPB_THT_LED_YELLOW);
    chSysInit();
    bcuCommunication_init();
    alarmClock_init();
    measurement_init();
    adcSTM32SetCCR(ADC_CCR_TSEN | ADC_CCR_VREFEN);

    while (true) {
        chThdSleepMilliseconds(10000);
    }
}
