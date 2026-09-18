#pragma once
#include <stdint.h>
namespace ambient {
void begin();
void poll(uint32_t now);
bool value(int16_t& tempTenthsC, uint16_t& humidityTenthsPct, uint32_t& updated);
bool checksumFailed();
}
