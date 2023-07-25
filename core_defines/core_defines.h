#ifndef BASE_PCU_CORE_DEFINES_H
#define BASE_PCU_CORE_DEFINES_H

#define DIMENSION(x) (uint8_t)(sizeof(x)/sizeof(x[0]))
#define UNUSED_PARAM(x) (void)(x)


typedef enum {
    pcu_dockingState7_12vFloating = -7,
    pcu_dockingState6_5vFloating = -6,
    pcu_dockingState5_allDocked5vOn = -5,
    pcu_dockingState4_allDocked12vOn = -4,
    pcu_dockingState3_allDockedPwrOn = -3,
    pcu_dockingState2_allDockedPwrOff = -2,
    pcu_dockingState1_Undocked = -1,
    pcuSUCCESS = 0,
    pcuFAIL = 1,
} pcu_returncode_e;

#endif //BASE_PCU_CORE_DEFINES_H
