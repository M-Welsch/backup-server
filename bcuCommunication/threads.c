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


static void cmd_led_on(BaseSequentialStream *chp, int argc, char *argv[]) {
  UNUSED_PARAM(chp);
  UNUSED_PARAM(argc);
  UNUSED_PARAM(argv);
  static char buffer[16];
  chsnprintf(buffer, 15, "Led is %s", argv[0]);
  putIntoOutputMailbox(buffer);
  palSetPad(GPIOB, GPIPB_THT_LED_YELLOW);
}

static void cmd_led_off(BaseSequentialStream *chp, int argc, char *argv[]) {
  UNUSED_PARAM(chp);
  UNUSED_PARAM(argc);
  UNUSED_PARAM(argv);
  putIntoOutputMailbox("Led aus\n");
  palClearPad(GPIOB, GPIPB_THT_LED_YELLOW);
}

static void cmd_current_date(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    static char buffer[64];
    alarmClock_getDate(buffer);
    putIntoOutputMailbox(buffer);
}

static void cmd_get_measurement_values(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    measurementValues_t values;
    measurement_getValues(&values);
    static char buffer[64];
    chsnprintf(buffer, 63, "adc: %i\n", values.stator_supply_sense);
    putIntoOutputMailbox(buffer);
}

static void cmd_get_endswitch(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    static char buffer[64];
    chsnprintf(buffer, 63, "endswitch: %i\n", measurement_getEndswitch());
    putIntoOutputMailbox(buffer);
}

static void cmd_powerHdd(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    powerHdd();
}

static void cmd_unpowerHdd(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    unpowerHdd();
}

static void cmd_powerBcu(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    powerBcu();
}

static void cmd_unpowerBcu(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    unpowerBcu();
}

static void cmd_dock(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    pcu_returncode_e success = dock();
    if (success == pcuSUCCESS) {
        putIntoOutputMailbox("docked successfully!");
    }
    else {
        putIntoOutputMailbox("docking failed!");
    }
//    testPwm();
}

static void cmd_undock(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    pcu_returncode_e success = undock();
    if (success == pcuSUCCESS) {
        putIntoOutputMailbox("undocked successfully!");
    }
    else {
        putIntoOutputMailbox("undocking failed!");
    }
}

static void cmd_get_dockingstate(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    pcu_dockingstate_e dockingState = getDockingState();
    if (dockingState == pcu_dockingState0_docked) {
        putIntoOutputMailbox("pcu_dockingState0_docked");
    }
    else if (dockingState == pcu_dockingState1_undocked) {
        putIntoOutputMailbox("pcu_dockingState1_undocked");
    }
    else if (dockingState == pcu_dockingState2_allDockedPwrOff) {
        putIntoOutputMailbox("pcu_dockingState2_allDockedPwrOff");
    }
    else if (dockingState == pcu_dockingState3_allDockedPwrOn){
        putIntoOutputMailbox("pcu_dockingState3_allDockedPwrOn");
    }
    else if (dockingState == pcu_dockingState4_allDocked12vOn) {
        putIntoOutputMailbox("pcu_dockingState4_allDocked12vOn");
    }
    else if (dockingState == pcu_dockingState5_allDocked5vOn) {
        putIntoOutputMailbox("pcu_dockingState5_allDocked5vOn");
    }
    else if (dockingState == pcu_dockingState6_5vFloating) {
        putIntoOutputMailbox("pcu_dockingState6_5vFloating");
    }
    else if (dockingState == pcu_dockingState7_12vFloating) {
        putIntoOutputMailbox("pcu_dockingState7_12vFloating");
    }
    else if (dockingState == pcu_dockingState9_inbetween) {
        putIntoOutputMailbox("pcu_dockingState9_inbetween");
    }
    else if (dockingState == pcu_dockingState_unknown){
        putIntoOutputMailbox("pcu_dockingState_unknown");
    }
    else {
        putIntoOutputMailbox("no idea. This shouldn't happen");
    }
}

static void cmd_get_stator_supply_sense(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    measurementValues_t values;
    measurement_getValues(&values);
    static char buffer[32];
    chsnprintf(buffer, 32, "%i", values.stator_supply_sense);
    putIntoOutputMailbox(buffer);
}

static void cmd_docking_getCurrentLog(BaseSequentialStream *chp, int argc, char *argv[]) {
    UNUSED_PARAM(chp);
    UNUSED_PARAM(argc);
    UNUSED_PARAM(argv);
    uint8_t msgCounter = 0;
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
        chsnprintf(buffer, CURRENT_LOG_BUFFER_SIZE * 4, "%s%i,", buffer, getFromCurrentLog(counter));
    }
    putIntoOutputMailbox(buffer);
}

static const ShellCommand commands[] = {
        {"led_on",                 cmd_led_on},
        {"led_off",                cmd_led_off},
        {"current_date",           cmd_current_date},
        {"get_measurement_values", cmd_get_measurement_values},
        {"get_endswitch",          cmd_get_endswitch},
        {"power_hdd",              cmd_powerHdd},
        {"unpower_hdd",            cmd_unpowerHdd},
        {"power_bcu",              cmd_powerBcu},
        {"unpower_bcu",            cmd_unpowerBcu},
        {"dock",                   cmd_dock},
        {"undock",                 cmd_undock},
        {"get_dockingstate",       cmd_get_dockingstate},
        {"get_status_supply_sense",cmd_get_stator_supply_sense},
        {"get_docking_current_log",cmd_docking_getCurrentLog},
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
