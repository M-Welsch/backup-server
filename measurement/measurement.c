#include "measurement.h"
#include "hal.h"

volatile uint32_t adc_result = 0;

void adcCbConv(ADCDriver *adcp) {
    (void)adcp;
}

static const ADCConversionGroup adcgrpcfg1 = {
    FALSE,
    1,
    adcCbConv,
    NULL,
    ADC_CFGR1_CONT | ADC_CFGR1_RES_12BIT,             /* CFGR1 */
    ADC_TR(0, 0),                                     /* TR */
    ADC_SMPR_SMP_1P5,                                 /* SMPR */
    ADC_CHSELR_CHSEL10                                /* CHSELR */
};

void measurement_init(void) {
    adcStart(&ADCD1, NULL);
}

void measurement_getValues(measurementValues_t *values) {
    adcsample_t samples[10];
    adcConvert(&ADCD1, &adcgrpcfg1, samples, 1);
    values->adc1 = samples[0];
}
