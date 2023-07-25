#ifndef BASE_PCU_MEASUREMENT_H
#define BASE_PCU_MEASUREMENT_H

#include <stdint-gcc.h>

typedef struct {
    uint16_t adc1;
    uint16_t adc2;
} measurementValues_t;

void measurement_init(void);
void measurement_getValues(measurementValues_t *values);

#endif //BASE_PCU_MEASUREMENT_H
