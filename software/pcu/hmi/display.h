//
// Created by max on 01.10.23.
//

#ifndef BASE_PCU_DISPLAY_H
#define BASE_PCU_DISPLAY_H

#include "core_defines.h"

pcu_returncode_e display_init(void);
pcu_returncode_e display_write(const char* lines);
pcu_returncode_e display_clear(void);
pcu_returncode_e display_dim(const uint8_t brightness_percent);

#endif //BASE_PCU_DISPLAY_H
