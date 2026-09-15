#pragma once
#include <stdint.h>
namespace alarm {
void begin();
void set(uint8_t state);
void heartbeat();
void poll();
}
