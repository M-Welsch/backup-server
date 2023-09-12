#include <string.h>
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
        chprintf(chp, "pcu_dockingState0_docked");
    }
    else if (dockingState == pcu_dockingState1_undocked) {
        chprintf(chp, "pcu_dockingState1_undocked");
    }
    else if (dockingState == pcu_dockingState2_allDockedPwrOff) {
        chprintf(chp, "pcu_dockingState2_allDockedPwrOff");
    }
    else if (dockingState == pcu_dockingState3_allDockedPwrOn){
        chprintf(chp, "pcu_dockingState3_allDockedPwrOn");
    }
    else if (dockingState == pcu_dockingState4_allDocked12vOn) {
        chprintf(chp, "pcu_dockingState4_allDocked12vOn");
    }
    else if (dockingState == pcu_dockingState5_allDocked5vOn) {
        chprintf(chp, "pcu_dockingState5_allDocked5vOn");
    }
    else if (dockingState == pcu_dockingState6_5vFloating) {
        chprintf(chp, "pcu_dockingState6_5vFloating");
    }
    else if (dockingState == pcu_dockingState7_12vFloating) {
        chprintf(chp, "pcu_dockingState7_12vFloating");
    }
    else if (dockingState == pcu_dockingState9_inbetween) {
        chprintf(chp, "pcu_dockingState9_inbetween");
    }
    else if (dockingState == pcu_dockingState_unknown){
        chprintf(chp, "pcu_dockingState_unknown");
    }
    else {
        chprintf(chp, "no idea. This shouldn't happen");
    }
}

static void _getCurrentLog(BaseSequentialStream *chp) {
    static char buffer[CURRENT_LOG_BUFFER_SIZE * 5];
    for(uint16_t strcnt = 0; strcnt < CURRENT_LOG_BUFFER_SIZE * 4; strcnt++) {
        buffer[strcnt] = '\0';
    }
    uint16_t currentValue = 0;
    for(uint16_t counter = 0; counter < CURRENT_LOG_BUFFER_SIZE; counter++) {
        currentValue = getFromCurrentLog(counter);
        if (currentValue == 0) {
            break;
        }
        chprintf( chp, "%i,", buffer, getFromCurrentLog(counter));
    }
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
        digitalValue = measurement_getEndswitch();
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
    else {
        chprintf(chp, "wtf is %s?\n", what_to_power);
        return pcuFAIL;
    }
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

static void cmd_get(BaseSequentialStream *chp, int argc, char *argv[]) {
    if (argc < 1) {
        _argument_missing(chp);
        return;
    }
    if(isEqual(argv[0], "dockingstate")) {
        _get_dockingstate(chp);
    }
    else if(isEqual(argv[0], "analog")) {
        if (argc < 2) {
            _argument_missing(chp);
            return;
        }
        _get_analog_value(chp, argv[1]);
    }
    else if (isEqual(argv[0], "digital")) {
        if (argc < 2) {
            _argument_missing(chp);
            return;
        }
        _get_digital_value(chp, argv[1]);
    }
    else if (isEqual(argv[0], "date")) {
        static char buffer[64];
        alarmClock_getDate(buffer);
        chprintf(chp, "%s\n", buffer);
    }
    else if (isEqual(argv[0], "current_log")) {
        _getCurrentLog(chp);
    }
    else {
        chprintf(chp, "invalid\n");
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
        chprintf(chp, "not implemented yet\n");
    }
    else {
        chprintf(chp, "invalid\n");
    }
}

static void cmd_testForEcho(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    chprintf(chp, "Echo");
}

static const ShellCommand commands[] = {
        {"get", cmd_get},
        {"set", cmd_set},
        {"probe", cmd_testForEcho},
        {"cmd", cmd},
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
