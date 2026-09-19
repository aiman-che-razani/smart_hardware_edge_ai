#include "alarm.h"
#include <Arduino.h>
#include "config.h"
namespace { uint32_t lastHost=0; uint8_t state=3; }
namespace alarm {
void set(uint8_t value) {
    state=value;
    digitalWrite(sentinel::kGreen, state==0);
    digitalWrite(sentinel::kAmber, state==1 || state==3);
    digitalWrite(sentinel::kRed, state==2);
    // Passive piezo buzzer: needs an oscillating drive signal, not a static level.
    if (state==2) tone(sentinel::kBuzzer, sentinel::kBuzzerHz);
    else noTone(sentinel::kBuzzer);
}
void begin() {
    for (uint8_t pin=sentinel::kGreen;pin<=sentinel::kBuzzer;++pin) {
        digitalWrite(pin, LOW); pinMode(pin, OUTPUT);
    }
    set(3);
}
void heartbeat() { lastHost=millis(); }
void poll() {
    if (uint32_t(millis()-lastHost)>3000 && state!=2) set(3);
    // FAULT remains latched on host loss; explicit recovery command clears it.
}
}
