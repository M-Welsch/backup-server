#include <string.h>
#include <stdlib.h>
#include "ch.h"
#include "hal.h"
#include "usbcfg.h"
#include "shell.h"
#include "chprintf.h"
#include "threads.h"
#include "core_defines.h"

#include "alarmClock.h"
#include "measurement.h"
#include "docking.h"
#include "power.h"
#include "statemachine.h"
#include "pcu_events.h"
#include "display.h"
#include "hmi.h"

/** @brief mailbox for messages to BaSe BCU */
mailbox_t bcu_comm_mb;
msg_t bcu_comm_mb_buffer[BCU_COMM_MB_BUFFER_SIZE];

void _initializeMailbox(void) {
  chMBObjectInit(&bcu_comm_mb, bcu_comm_mb_buffer, BCU_COMM_MB_BUFFER_SIZE);
}

static void _bcuCommunicationOutputMainloop(BaseSequentialStream *stream) {
  msg_t msg = 0;
  chMBFetchTimeout(&bcu_comm_mb, &msg, TIME_INFINITE);
  const char *s_msg = (const char *)msg;
  chprintf(stream, "%s\n", s_msg);
}

static THD_WORKING_AREA(bcuCommunicationOutputThread, 128);
static THD_FUNCTION(bcuCommunicationOutput, arg) {
  UNUSED_PARAM(arg);
  chRegSetThreadName("BCU Communication Output Thread");
  BaseSequentialStream *stream = (BaseSequentialStream *) &SDU1;
  while (true) {
    _bcuCommunicationOutputMainloop(stream);
  }
}

msg_t putIntoOutputMailbox(char* msg) {
  return chMBPostTimeout(&bcu_comm_mb, (msg_t) msg, TIME_MS2I(200));
}

#define SHELL_WA_SIZE   THD_WORKING_AREA_SIZE(2048)


static void _get_dockingstate(BaseSequentialStream *chp) {
    pcu_dockingstate_e dockingState = getDockingState();
    if (dockingState == pcu_dockingState0_docked) {
        chprintf(chp, "pcu_dockingState0_docked\n");
    }
    else if (dockingState == pcu_dockingState1_undocked) {
        chprintf(chp, "pcu_dockingState1_undocked\n");
    }
    else if (dockingState == pcu_dockingState2_allDockedPwrOff) {
        chprintf(chp, "pcu_dockingState2_allDockedPwrOff\n");
    }
    else if (dockingState == pcu_dockingState3_allDockedPwrOn){
        chprintf(chp, "pcu_dockingState3_allDockedPwrOn\n");
    }
    else if (dockingState == pcu_dockingState4_allDocked12vOn) {
        chprintf(chp, "pcu_dockingState4_allDocked12vOn\n");
    }
    else if (dockingState == pcu_dockingState5_allDocked5vOn) {
        chprintf(chp, "pcu_dockingState5_allDocked5vOn\n");
    }
    else if (dockingState == pcu_dockingState6_5vFloating) {
        chprintf(chp, "pcu_dockingState6_5vFloating\n");
    }
    else if (dockingState == pcu_dockingState7_12vFloating) {
        chprintf(chp, "pcu_dockingState7_12vFloating\n");
    }
    else if (dockingState == pcu_dockingState9_inbetween) {
        chprintf(chp, "pcu_dockingState9_inbetween\n");
    }
    else if (dockingState == pcu_dockingState_unknown){
        chprintf(chp, "pcu_dockingState_unknown\n");
    }
    else {
        chprintf(chp, "no idea. This shouldn't happen\n");
    }
}

static void _getCurrentLog(BaseSequentialStream *chp) {
    uint16_t currentValue = 0;
    uint16_t counter = 0;
    while (getFromCurrentLog(&currentValue, counter)) {
        chprintf(chp, "%i,", currentValue);
        counter++;
    }
    chprintf(chp, "\n");
}

static void _getCurrentState(BaseSequentialStream *chp) {
    uint8_t  state = (uint8_t) statemachine_getCurrentState();
    chprintf(chp, "%d\n", state);
}

static inline bool isEqual(const char *buffer, const char *string) {
    return strcmp((char *) buffer, string) == 0;
}

static void _get_analog_value(BaseSequentialStream *chp, const char *channel) {
    measurementValues_t values;
    measurement_getValues(&values);
    uint16_t value = 0;
    if (isEqual(channel, "stator_supply_sense")) {
        value = values.stator_supply_sense;
    }
    else if (isEqual(channel, "imotor_prot")) {
        value = values.imotor_prot;
    }
    else if (isEqual(channel, "vin12_meas")) {
        value = values.vin12_meas;
    }
    else {
        chprintf(chp, "Error: invalid channel %s\n", channel);
        return;
    }
    chprintf(chp, "%i\n", value);
}

static void _get_digital_value(BaseSequentialStream *chp, const char *channel) {
    int digitalValue = 0;
    if (isEqual(channel, "endswitch")) {
        digitalValue = measurement_getButton(UNDOCKED_ENDSWITCH);
    }
    else if (isEqual(channel, "docked")) {
        digitalValue = measurement_getDocked();
    }

    if (digitalValue) {
        chprintf(chp, "true\n");
    }
    else {
        chprintf(chp, "false\n");
    }
}

static void _argument_missing(BaseSequentialStream *chp) {
    chprintf(chp, "Error: argument missing\n");
}

static pcu_returncode_e _power(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 2) {
        _argument_missing(chp);
        return pcuFAIL;
    }
    char *what_to_power = argv[0];
    char *desired_state = argv[1];
    bool on = false;

    if (isEqual(desired_state, "on")) {
        on = true;
    }
    else if (isEqual(desired_state, "off")) {
        on = false;
    }
    else {
        chprintf(chp, "either on or off");
        return pcuFAIL;
    }

    if (isEqual(what_to_power, "hdd")) {
        if (on) {
            return powerHdd();
        }
        else {
            return unpowerHdd();
        }
    }
    else if (isEqual(what_to_power, "bcu")) {
        if (on) {
            return powerBcu();
        }
        else {
            return unpowerBcu();
        }
    }
    else if (isEqual(what_to_power, "5v")) {
        if (on) {
            return power5v();
        }
        else {
            return unpower5v();
        }
    }
    else {
        chprintf(chp, "wtf is %s?\n", what_to_power);
        return pcuFAIL;
    }
}

static pcu_returncode_e _cmdShutdown(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return pcuFAIL;
    }
    const char *init_or_abort = argv[0];
    if (isEqual(init_or_abort, "init")) {
        uint32_t milliseconds_to_shutdown = DEFAULT_MILLISECONDS_TO_SHUTDOWN;
        if (argc == 2) {
            char *endPtr;
            milliseconds_to_shutdown = (uint32_t) strtol(argv[1], &endPtr, 10);
            if (milliseconds_to_shutdown > MAXIMUM_MILLISECONDS_TO_SHUTDOWN) {
                milliseconds_to_shutdown = DEFAULT_MILLISECONDS_TO_SHUTDOWN;
                chprintf(chp, "custom timeout for shutdown exceeded limit of %d, defaulting to %d.", MAXIMUM_MILLISECONDS_TO_SHUTDOWN, DEFAULT_MILLISECONDS_TO_SHUTDOWN);
            }
            else {
                chprintf(chp, "setting custom timeout of %d ms\n", milliseconds_to_shutdown);
            }
        }
        statemachine_setMillisecondsToShutdown(milliseconds_to_shutdown);  // set this in any case to enforce the default if nothing else is said
        statemachine_sendEvent(EVENT_SHUTDOWN_REQUESTED);
    }
    else if (isEqual(init_or_abort, "abort")) {
        statemachine_sendEvent(EVENT_SHUTDOWN_ABORTED);
    }
    else {
        return pcuFAIL;
    }
    return pcuSUCCESS;
}

static pcu_returncode_e _cmdWakeup(void) {
    statemachine_sendEvent(EVENT_WAKEUP_REQUESTED_BY_USER);
    return pcuSUCCESS;
}

static void cmd(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    char *command = argv[0];
    pcu_returncode_e success = pcuFAIL;
    if (isEqual(command, "dock")) {
        success = dock();
    }
    else if (isEqual(command, "undock")) {
        success = undock();
    }
    else if (isEqual(command, "power")) {
        success = _power(chp, argc-1, argv+1);
    }
    else if (isEqual(command, "shutdown")) {
        success = _cmdShutdown(chp, argc-1, argv+1);
    }
    else if (isEqual(command, "wakeup")) {
        success = _cmdWakeup();
    }
    else {
        chprintf(chp, "invalid command %s\n", command);
    }

    if (success == pcuSUCCESS) {
        chprintf(chp, "%s successful\n", command);
    }
    else {
        chprintf(chp, "%s failed\n", command);
    }
}

static void debugcmd(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    char *command = argv[0];
    pcu_returncode_e success = pcuFAIL;
    if (isEqual(command, "wakeup")) {
        success = _cmdWakeup();
    }
    else if (isEqual(command, "button_0_pressed")) {
        statemachine_sendEvent(EVENT_BUTTON_0_PRESSED);
        success = pcuSUCCESS;
    }
    else if (isEqual(command, "button_1_pressed")) {
        statemachine_sendEvent(EVENT_BUTTON_1_PRESSED);
        success = pcuSUCCESS;
    }
    else {
        chprintf(chp, "invalid command %s\n", command);
    }

    if (success == pcuSUCCESS) {
        chprintf(chp, "%s successful\n", command);
    }
    else {
        chprintf(chp, "%s failed\n", command);
    }
}

static void _getDate(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    char *whichDateToGet = argv[0];
    char buffer[64];
    RTCDateTime timespec;
    if (isEqual(whichDateToGet, "now")) {
        alarmClock_getDateNow(&timespec);
        alarmClock_RtcDateTimeToStr(buffer, &timespec);
    }
    else if (isEqual(whichDateToGet, "wakeup"))  {
        alarmClock_getDateWakeup(&timespec);
        alarmClock_RtcDateTimeToStr(buffer, &timespec);
    }
    else if (isEqual(whichDateToGet, "backup")) {
        alarmClock_getDateBackup(&timespec);
        alarmClock_RtcDateTimeToStr(buffer, &timespec);
    }
    else {
        chsnprintf(buffer, 64, "no such date as %s", whichDateToGet);
    }
    chprintf(chp, "%s\n", buffer);
}

static pcu_returncode_e _getWakeupReason(BaseSequentialStream *chp) {
    wakeup_reason_e wakeup_reason = statemachine_getWakeupReason();
    switch (wakeup_reason) {
        case WAKEUP_REASON_POWER_ON:
            chprintf(chp, "poweron\n");
            break;
        case WAKEUP_REASON_USER_REQUEST:
            chprintf(chp, "requested\n");
            break;
        case WAKEUP_REASON_SCHEDULED:
            chprintf(chp, "scheduled\n");
            break;
        default:
            return pcuFAIL;
    }
    return pcuSUCCESS;
}


static void cmd_get(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    const char *whatToGet = argv[0];
    if(isEqual(whatToGet, "dockingstate")) {
        _get_dockingstate(chp);
    }
    else if (isEqual(whatToGet, "wakeupreason")) {
        _getWakeupReason(chp);
    }
    else if(isEqual(whatToGet, "analog")) {
        if (argc < 2) {
            _argument_missing(chp);
            return;
        }
        _get_analog_value(chp, argv[1]);
    }
    else if (isEqual(whatToGet, "digital")) {
        if (argc < 2) {
            _argument_missing(chp);
            return;
        }
        _get_digital_value(chp, argv[1]);
    }
    else if (isEqual(whatToGet, "date")) {
        _getDate(chp, argc-1, argv+1);
    }
    else if (isEqual(whatToGet, "currentlog")) {
        _getCurrentLog(chp);
    }
    else if (isEqual(whatToGet, "currentstate")) {
        _getCurrentState(chp);
    }
    else {
        chprintf(chp, "invalid\n");
    }
}

/**
 * @brief sets different kinds of dates. Those can be "now", "backup" and "wakeup". Details see github issue
 * @details argv[0] is one of "now", "backup" or "wakeup"
 *          argv[1] is the year. eg. 2023
 *          argv[2] is month from 1-12
 *          argv[3] is the day of month
 *          argv[4] is the hour
 *          argv[5] is a minute.
 *          an example would be "set date wakeup 2023 11 04 12 00" to wake BaSe at 4. Nov. 2023 at 12:00
 * @param chp
 * @param argc
 * @param argv
 */
static void _setDate(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 6) {
        _argument_missing(chp);
        return;
    }
    RTCDateTime timespec;
    if (alarmClock_argsToRtcDateTime(&timespec, argc-1, argv+1) != pcuSUCCESS) {
        chprintf(chp, "Conversion Error or so");
    }

    if (isEqual(argv[0], "now")) {
        alarmClock_setDateNow(&timespec);
    }
    else if (isEqual(argv[0], "wakeup")) {
        alarmClock_setDateWakeup(&timespec);
    }
    else if (isEqual(argv[0], "backup")) {
        alarmClock_setDateBackup(&timespec);
    }
}

static void _setDisplay(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    if (isEqual(argv[0], "text")) {
        /* FIXME: cannot display new line. Maybe put in second argument */
        display_write(argv[1]);
    }
    else if (isEqual(argv[0], "brightness")) {
        char *endPtr;
        uint8_t brightness = (uint8_t) strtol(argv[1], &endPtr, 10);
        display_dim(brightness);
    }
    else {
        ;
    }
}

static void _setLed(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    /* Todo: implement correctly */
    if (isEqual(argv[0], "on")) {
        hmi_led_dim(100);
    }
    if (isEqual(argv[0], "off")) {
        hmi_led_dim(0);
    }

}


static void cmd_set(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    if(isEqual(argv[0], "date")) {
        _setDate(chp, argc-1, argv+1);
    }
    else if (isEqual(argv[0], "display")) {
        _setDisplay(chp, argc-1, argv+1);
    }
    else if (isEqual(argv[0], "led")) {
        _setLed(chp, argc-1, argv+1);
    }
    else {
        chprintf(chp, "invalid\n");
    }
}

static void cmd_testForEcho(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    chprintf(chp, "Echo\n");
}

static const ShellCommand commands[] = {
        {"get", cmd_get},
        {"set", cmd_set},
        {"probe", cmd_testForEcho},
        {"cmd", cmd},
        {"debugcmd", debugcmd},
        {NULL, NULL}
};

static ShellConfig shell_cfg1 = {
        (BaseSequentialStream *)&SDU1,
        commands
};

static void _bcuCommunicationInputMainloop(void) {
  if (SDU1.config->usbp->state == USB_ACTIVE) {
    thread_t *shelltp = chThdCreateFromHeap(NULL, SHELL_WA_SIZE, "shell", NORMALPRIO+1, shellThread, (void *)&shell_cfg1);
    chThdWait(shelltp);
  }
  else {
      chThdSleepMilliseconds(100);
  }
}

static THD_WORKING_AREA(bcuCommunicationInputThread, 128);
static THD_FUNCTION(bcuCommunicationInput, arg) {
  UNUSED_PARAM(arg);
  chRegSetThreadName("BCU Communication Input Thread");
  while (true) {
    _bcuCommunicationInputMainloop();
  }
}

void bcuCommunicationThreads_init(void) {
  _initializeMailbox();
  shellInit();
  chThdCreateStatic(bcuCommunicationOutputThread, sizeof(bcuCommunicationOutputThread), NORMALPRIO, bcuCommunicationOutput, NULL);
  chThdCreateStatic(bcuCommunicationInputThread, sizeof(bcuCommunicationInputThread), NORMALPRIO+1, bcuCommunicationInput, NULL);
}
