#include "analog_environment.h"
#include <Arduino.h>
#include "config.h"
namespace {
uint16_t averaged(uint8_t pin) {
    uint16_t total = 0;
    for (uint8_t i = 0; i < 4; ++i) total += analogRead(pin);
    return total / 4;
}
}
namespace analogEnvironment {
void begin() {
    pinMode(sentinel::kThermistorPin, INPUT);
    pinMode(sentinel::kLightPin, INPUT);
}
uint16_t thermistor() { return averaged(sentinel::kThermistorPin); }
uint16_t light() { return averaged(sentinel::kLightPin); }
}
