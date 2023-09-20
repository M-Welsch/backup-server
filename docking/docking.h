#ifndef BASE_PCU_DOCKING_H
#define BASE_PCU_DOCKING_H

#include <stdint-gcc.h>
#include <stdbool.h>
#include "core_defines.h"

#define MAXIMUM_DOCKING_TIME_1MS_TICKS 2000
#define MAXIMUM_OVERCURRENT_INRUSH_SAMPLES 100
#define MAXIMUM_CONSECUTIVE_OVERCURRENT_SAMPLES 10
#define CURRENT_LOG_BUFFER_SIZE 200

pcu_returncode_e dockingInit(void);

pcu_returncode_e dock(void);
pcu_returncode_e undock(void);

pcu_returncode_e powerHdd(void);
pcu_returncode_e unpowerHdd(void);

pcu_returncode_e powerBcu(void);
pcu_returncode_e unpowerBcu(void);

pcu_dockingstate_e getDockingState(void);
bool getFromCurrentLog(uint16_t *outval, const uint16_t ptr);

#endif //BASE_PCU_DOCKING_H
