#pragma once
#include <cstdint>
#include <vector>

// Zero starts the game; positive is a cancelled picker; negative is an error.
int wetrix_load_rom(int argc, char** argv, std::vector<uint8_t>& rom);
