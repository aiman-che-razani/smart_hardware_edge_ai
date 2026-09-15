#pragma once
#include <stdint.h>
namespace acceleration {
bool begin();
uint8_t pending();
bool overrun();
void read(int16_t* xyz);
}
