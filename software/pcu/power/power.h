//
// Created by max on 22.09.23.
//

#ifndef BASE_PCU_POWER_H
#define BASE_PCU_POWER_H

#include "core_defines.h"

pcu_returncode_e powerHdd(void);
pcu_returncode_e unpowerHdd(void);

pcu_returncode_e powerBcu(void);
pcu_returncode_e unpowerBcu(void);

pcu_returncode_e power5v(void);
pcu_returncode_e unpower5v(void);

#endif //BASE_PCU_POWER_H
