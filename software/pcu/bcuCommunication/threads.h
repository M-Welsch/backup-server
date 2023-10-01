#ifndef BASE_PCU_THREADS_H
#define BASE_PCU_THREADS_H

#define BCU_COMM_MB_BUFFER_SIZE 256
#define BCU_COMM_INPUT_BUFFER_SIZE 256

#include "ch.h"

extern mailbox_t bcu_comm_mb;
extern msg_t bcu_comm_mb_buffer[BCU_COMM_MB_BUFFER_SIZE];

void bcuCommunicationThreads_init(void);
msg_t putIntoOutputMailbox(char* msg);

#endif //BASE_PCU_THREADS_H
