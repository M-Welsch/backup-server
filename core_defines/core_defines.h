#ifndef BASE_PCU_CORE_DEFINES_H
#define BASE_PCU_CORE_DEFINES_H

#define DIMENSION(x) (uint8_t)(sizeof(x)/sizeof(x[0]))
#define UNUSED_PARAM(x) (void)(x)


typedef enum {
    pcuSUCCESS = 0,
    pcuFAIL = 1,
} pcu_returncode_e;

#endif //BASE_PCU_CORE_DEFINES_H
