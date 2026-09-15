#pragma once
#include "types.h"
namespace transport {
void begin(uint32_t boot);
void poll();
bool send(const Sample& sample);
bool streaming();
void status();
}
