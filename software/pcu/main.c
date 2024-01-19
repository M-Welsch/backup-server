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
#include "bcuCommunication.h"
#include "alarmClock.h"
#include "measurement.h"
#include "docking.h"
#include "statemachine.h"
#include "hmi/hmi.h"
#include "debug.h"

int main(void) {
    halInit();
    dockingInit();

    chSysInit();
    debug_init();
    debug_log("[I] PCU powered up\n");
    bcuCommunication_init();
    alarmClock_init();
    measurement_init();
    statemachine_init();
    hmi_init();

    while (true) {
        chThdSleepMilliseconds(1000);
    }
}
