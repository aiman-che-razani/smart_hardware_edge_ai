#include "water_level.h"
#include <Arduino.h>
#include "config.h"
namespace waterLevel {
void begin() { pinMode(sentinel::kWaterLevelPin, INPUT); }
uint16_t read() { return analogRead(sentinel::kWaterLevelPin); }
}
