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
#include "chprintf.h"

#include "usbcfg.h"
//
//typedef enum
//{
//    stFAIL = 0,     /**< Error, operation fail */
//    stSUCCESS = 1   /**< Operation success*/
//} returnCode_e;
//
void startUsb(void);
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


static THD_WORKING_AREA(blinkerThread, 128);
static THD_FUNCTION(Blinker, arg) {

  (void)arg;
  chRegSetThreadName("blinker");
  BaseSequentialStream *chp = (BaseSequentialStream*) &SDU1;
  while (true) {
    palClearPad(GPIOA, GPIOA_LED_GREEN);
    palClearPad(GPIOA, MOTOR_DRV1);
    palSetPad(GPIOA, MOTOR_DRV2);
    uint32_t endswitch_state = palReadPad(GPIOB, nENDSWITCH_UNDOCKED);
    chprintf(chp, "Endswitch: %i", endswitch_state);
    chThdSleepMilliseconds(1000);
    palSetPad(GPIOA, GPIOA_LED_GREEN);
    palClearPad(GPIOA, MOTOR_DRV2);
    palSetPad(GPIOA, MOTOR_DRV1);
    chprintf(chp, "Off");
    chThdSleepMilliseconds(1000);
  }
}


int main(void) {

  /*
   * System initializations.
   * - HAL initialization, this also initializes the configured device drivers
   *   and performs the board-specific initializations.
   * - Kernel initialization, the main() function becomes a thread and the
   *   RTOS is active.
   */
  halInit();
  chSysInit();
  startUsb();


    /*
     * Creates the blinker thread.
     */
  chThdCreateStatic(blinkerThread, sizeof(blinkerThread), NORMALPRIO, Blinker, NULL);
//  chThdCreateStatic(statemachineThread, sizeof(statemachineThread), NORMALPRIO, Statemachine, NULL);

  /*
   * Normal main() thread activity, in this demo it does nothing except
   * sleeping in a loop and check the button state.
   */
  while (true) {
    if (!palReadPad(GPIOC, GPIOC_BUTTON)) {
      test_execute((BaseSequentialStream *)&SD2, &rt_test_suite);
      test_execute((BaseSequentialStream *)&SD2, &oslib_test_suite);
    }
    chThdSleepMilliseconds(500);
  }
}

void startUsb() {/*
 * Initializes a serial-over-USB CDC driver.
 */
    sduObjectInit(&SDU1);
    sduStart(&SDU1, &serusbcfg);

    /*
     * Activates the USB driver and then the USB bus pull-up on D+.
     * Note, a delay is inserted in order to not have to disconnect the cable
     * after a reset.
     */
    usbDisconnectBus(serusbcfg.usbp);
    chThdSleepMilliseconds(1500);
    usbStart(serusbcfg.usbp, &usbcfg);
    usbConnectBus(serusbcfg.usbp);


    /*
       * Activates the serial driver 2 using the driver default configuration.
       */
    sdStart(&SD2, NULL);
}
