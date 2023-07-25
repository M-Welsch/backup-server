#ifndef BASE_PCU_DOCKING_H
#define BASE_PCU_DOCKING_H

#include "core_defines.h"

pcu_returncode_e dock(void);
pcu_returncode_e undock(void);

pcu_returncode_e powerHdd(void);
pcu_returncode_e unpowerHdd(void);

#endif //BASE_PCU_DOCKING_H
