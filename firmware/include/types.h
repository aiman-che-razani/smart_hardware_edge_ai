#pragma once
#include <stdint.h>

struct Sample {
    uint32_t boot, sequence, timestamp;
    uint16_t distance, distanceAge;
    uint16_t waterLevel, thermistor, light;
    int16_t ambientTemperature;
    uint16_t ambientHumidity, ambientAge;
    uint8_t flags;
};
static_assert(sizeof(Sample) == 29, "AVR wire layout changed");
