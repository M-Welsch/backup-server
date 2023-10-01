#ifndef BASE_PCU_HMI_H
#define BASE_PCU_HMI_H

#include "core_defines.h"

void hmi_init(void);
pcu_returncode_e hmi_led_dim(const uint8_t brightness_percent);

#endif //BASE_PCU_HMI_H
