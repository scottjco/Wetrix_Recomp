#pragma once
#include <cstdint>
bool wetrix_input_init(void* window);
void wetrix_input_poll();
uint32_t wetrix_input_state(unsigned player = 0);
bool wetrix_input_connected(unsigned player);
uint8_t wetrix_input_present_mask();

void wetrix_input_key(unsigned key);
