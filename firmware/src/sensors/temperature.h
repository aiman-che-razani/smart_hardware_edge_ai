#pragma once
#include <stdint.h>
namespace temperature {
bool begin();
void poll(uint32_t now);
bool value(int16_t& raw, uint32_t& updated);
}
