#ifndef BASE_PCU_BCUCOMMUNICATION_H
#define BASE_PCU_BCUCOMMUNICATION_H

#include "threads.h"
#include "core_defines.h"

void bcuCommunication_init(void);

pcu_returncode_e sendToBcu(char* msg);

#endif //BASE_PCU_BCUCOMMUNICATION_H
