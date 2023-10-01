#include "hal.h"

#include "display.h"

#define DISPLAY_DATA_BIT_MASK   ((1<<HMI_NSS2_DISPLAY_DB4) | \
                                (1<<HMI_SCK2_SCL2_DISPLAY_DB5) | \
                                (1<<HMI_MISO2_SDA2_DISPLAY_DB6) |\
                                (1<<HMI_MOSI2_DISPLAY_DB7))

void _enable(void) {
    palSetLine(LINE_HMI_USART_RX3_DISPLAY_E);
    chThdSleepMilliseconds(10);
    palClearLine(LINE_HMI_USART_RX3_DISPLAY_E);
    chThdSleepMilliseconds(10);
}

void _setRs(void) {
    palSetLine(LINE_HMI_USART_TX3_DISPLAY_RS);
}

void _clearRs(void) {
    palClearLine(LINE_HMI_USART_TX3_DISPLAY_RS);
}

void _outputData(uint8_t data_nibble) {
    uint32_t bits = (data_nibble << 12) & 0b1111000000000000;
    palSetPort(GPIOB, bits);
    uint32_t bits_to_clear = ~bits & 0b1111000000000000;
    palClearPort(GPIOB, bits_to_clear);
}

pcu_returncode_e display_init(void) {
    _outputData(0x00);
    /* refering to datasheet SPLC780D and (more importantly) lcd.py of "old" BaSe implementation*/
    chThdSleepMilliseconds(100);
    _clearRs();

    _outputData(0x03);
    _enable();
    chThdSleepMilliseconds(1);
    _outputData(0x03);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x03);
    _enable();
    chThdSleepMilliseconds(1);
    _outputData(0x02);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x02);
    _enable();
    chThdSleepMilliseconds(1);
    /* the following instruction ...
       DB7 DB6 DB5 DB4 |
       N   F   X   X   | N = HIGH => 2 lined display. F = don't care = 0
       1   0   0   0 => 0x8 */
    _outputData(0x08);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x00);
    _enable();
    chThdSleepMilliseconds(1);
    /* The following instruction ...
       DB7 DB6 DB5 DB4 |
       1   D   C   B   |
           |   |   +------B: Cursor ON/OFF control bit. B = LOW => Cursor blink is off
           |   +----------C: Cursor Control Bit. C = LOW => Cursor disappears
           +--------------D: Display ON/OFF control bit. D = HIGH => Display is on
       1   1   0   0 => 0xC */
    _outputData(0x0C);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x00);
    _enable();
    chThdSleepMilliseconds(1);
    _outputData(0x06);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x00);
    _enable();
    chThdSleepMilliseconds(1);

    /* DB7 DB6 DB5 DB4 |
       0   1   I/D S
               |   +--- S: LOW => no shift
               +------- I/D: HIGH => shift to the right (if S == HIGH)
               0   1   1   0x6*/
    _outputData(0x06);
    _enable();
    chThdSleepMilliseconds(1);

    _outputData(0x00);
    _enable();
    chThdSleepMilliseconds(1);
    _outputData(0x01);
    _enable();
    chThdSleepMilliseconds(1);
    return pcuSUCCESS;
}

void _writeChar(const char c) {
    _setRs();
    _outputData(c >> 4);
    _enable();
    _outputData(c);
    _enable();
}

pcu_returncode_e display_clear(void) {
    _clearRs();
    _outputData(0x00);
    _enable();
    _outputData(0x01);
    _enable();
    chThdSleepMilliseconds(1);
    return pcuSUCCESS;
}

void _nextLine(void) {
    _clearRs();
    _outputData(0xC);
    _enable();
    _outputData(0x0);
    _enable();
}

pcu_returncode_e display_write(const char* s) {
    display_clear();
    _setRs();
    while(*s!='\0') {
        if(*s == '\n') {
            _nextLine();
        }
        else {
            _writeChar(*s);
        }
        s++;
    }
    return pcuSUCCESS;
}



pcu_returncode_e display_dim(const uint8_t brightness_percent) {
    if (brightness_percent >= 50) {
        palSetLine(LINE_HMI_PWM0_DISPLAY);
    }
    else {
        palClearLine(LINE_HMI_PWM0_DISPLAY);
    }
    return pcuSUCCESS;
}
