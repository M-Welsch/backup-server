#include "chprintf.h"
#include "hal.h"
#include "chprintf.h"

#include "debug.h"

#define DEBUG_SERIAL_PORT SD1

void debug_init(void) {
    sdStart(&DEBUG_SERIAL_PORT, NULL);
}

void debug_log(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    chvprintf((BaseSequentialStream*) &DEBUG_SERIAL_PORT, fmt, args);
    va_end(args);
}
