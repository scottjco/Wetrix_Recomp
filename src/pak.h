#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
class WetrixPak {
    std::array<uint8_t,32768> bytes{};
    std::filesystem::path path;
    void store();
public:
    explicit WetrixPak(const std::filesystem::path& filename);
    void command(uint8_t* pif, uint32_t input, uint32_t input2 = 0, uint8_t present_mask = 3);
};
