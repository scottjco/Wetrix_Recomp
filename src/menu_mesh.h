#pragma once
#include <array>
#include <cstdint>

struct WetrixRimVertex {
    int16_t x, y, z;
    uint16_t flag;
    int16_t s, t;
    std::array<uint8_t, 4> normalAlpha;
};
static_assert(sizeof(WetrixRimVertex) == 16);
constexpr unsigned WetrixRimSegments = 128;
constexpr unsigned WetrixRimVertices = (WetrixRimSegments + 1) * 2;
constexpr unsigned WetrixRimCommandWords = (WetrixRimSegments * 3 + 1) * 2;
constexpr unsigned WetrixRimVertexBytes = WetrixRimVertices * 16;
constexpr unsigned WetrixRimListBytes = WetrixRimCommandWords * 4;
constexpr unsigned WetrixRimStorage = (WetrixRimVertexBytes + WetrixRimListBytes + 15) & ~15U;
constexpr unsigned WetrixMenuMeshReserve = WetrixRimStorage * 2;
constexpr uint32_t WetrixMenuBankBytes = 0x9D040;
struct WetrixSmoothRim {
    std::array<WetrixRimVertex, WetrixRimVertices> vertices;
    std::array<uint32_t, WetrixRimCommandWords> commands;
};
WetrixSmoothRim wetrix_build_smooth_rim(const std::array<WetrixRimVertex, 70>& native, uint32_t vertexAddress);
