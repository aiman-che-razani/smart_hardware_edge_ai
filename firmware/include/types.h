#pragma once
#include <stdint.h>

struct Sample {
    uint32_t boot, sequence, timestamp;
    int16_t ax, ay, az, shunt, temperature;
    uint16_t currentAge, temperatureAge;
    uint8_t flags;
};
static_assert(sizeof(Sample) == 27, "AVR wire layout changed");
