#ifndef BASE_PCU_MEASUREMENT_H
#define BASE_PCU_MEASUREMENT_H

#include <stdint-gcc.h>

typedef struct {
    uint16_t imotor_prot;
    uint16_t stator_supply_sense;
    uint16_t vin12_meas;

} measurementValues_t;

typedef enum {
    NOT_PRESSED,
    PRESSED
} switchState_t;

void measurement_init(void);
void measurement_getValues(measurementValues_t *values);
switchState_t measurement_getEndswitch(void);

#endif //BASE_PCU_MEASUREMENT_H
