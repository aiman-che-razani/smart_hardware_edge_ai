#pragma once

#include <stdint.h>

namespace sentinel {
#ifdef SENTINEL_CSV
constexpr uint32_t kConsoleBaud = 115200UL;
constexpr uint16_t kRate = 100;
#else
constexpr uint32_t kConsoleBaud = 500000UL;
constexpr uint16_t kRate = 800;
#endif
constexpr uint8_t kCs = 10, kTemperature = 4;
constexpr uint8_t kGreen = 5, kAmber = 6, kRed = 7, kBuzzer = 8;
constexpr uint16_t kShuntMilliohm = 100; // Must match actual breakout shunt.
constexpr uint16_t kAccelerationUg = 3900;
}  // namespace sentinel
