#include "ch.h"
#include "hal.h"
#include "usbcfg.h"
#include "shell.h"
#include "chprintf.h"
#include "threads.h"
#include "core_defines.h"

#include "alarmClock.h"
#include "measurement.h"

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
    chsnprintf(buffer, 63, "adc: %i\n", values.adc1);
    putIntoOutputMailbox(buffer);
}

static const ShellCommand commands[] = {
        {"led_on", cmd_led_on},
        {"led_off", cmd_led_off},
        {"current_date", cmd_current_date},
        {"get_measurement_values", cmd_get_measurement_values},
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
