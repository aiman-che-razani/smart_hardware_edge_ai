#pragma once
#include <stdint.h>
namespace ultrasonic {
void begin();
void poll(uint32_t now);
bool value(uint16_t& mm, uint32_t& updated);
}
