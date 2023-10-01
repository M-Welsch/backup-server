#ifndef BASE_PCU_MEASUREMENT_H
#define BASE_PCU_MEASUREMENT_H

#include <stdint-gcc.h>
#include <stdbool.h>

typedef struct {
    uint16_t imotor_prot;
    uint16_t stator_supply_sense;
    uint16_t vin12_meas;

} measurementValues_t;

typedef enum {
    NOT_PRESSED = 0U,
    PRESSED = 1U,
    AMBIGOUS
} switchState_t;

typedef enum {
    HMI_BUTTON_0,
    HMI_BUTTON_1,
    UNDOCKED_ENDSWITCH
} pushbutton_e;

void measurement_init(void);
void measurement_getValues(measurementValues_t *values);
switchState_t measurement_getButton(pushbutton_e pushbutton);
bool measurement_getDocked(void);

#endif //BASE_PCU_MEASUREMENT_H
