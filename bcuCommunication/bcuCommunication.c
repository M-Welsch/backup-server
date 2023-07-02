#include "usb.h"
#include "threads.h"
#include "bcuCommunication.h"

void bcuCommunication_init(void) {
  bcuCommunication_usb_init();
  bcuCommunicationThreads_init();
}

pcu_returncode_e sendToBcu(char* msg) {
  msg_t retval = putIntoOutputMailbox(msg);
  if (retval == MSG_OK) {
    return pcuSUCCESS;
  }
  else {
    return pcuFAIL;
  }
}
