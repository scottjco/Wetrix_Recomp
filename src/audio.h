#pragma once
#include <cstdint>
void wetrix_audio_task(uint8_t* rdram, uint32_t task);
uint32_t wetrix_audio_frequency(uint32_t hz);
uint32_t wetrix_audio_remaining(uint32_t maximum);
void wetrix_audio_queue(uint8_t* rdram, uint32_t address, uint32_t bytes);
