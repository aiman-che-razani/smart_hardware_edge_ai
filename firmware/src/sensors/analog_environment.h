#pragma once
#include <stdint.h>
namespace analogEnvironment {
void begin();
uint16_t thermistor();
uint16_t light();
}
