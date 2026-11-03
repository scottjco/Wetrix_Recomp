#pragma once
#include <cstdint>
bool wetrix_graphics_init(uint8_t* rdram, uint8_t* header);
void wetrix_graphics_task(uint8_t* rdram, uint32_t task);
bool wetrix_graphics_poll();
bool wetrix_graphics_present(uint8_t* rdram, uint32_t framebuffer, uint32_t mode, bool black);
