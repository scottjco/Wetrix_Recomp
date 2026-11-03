#ifndef WETRIX_BOOT_PROBE_H
#define WETRIX_BOOT_PROBE_H
#include "recomp.h"
void probe_osInitialize(uint8_t* rdram, recomp_context* ctx);
void probe_osStartThread(uint8_t* rdram, recomp_context* ctx);
#endif
