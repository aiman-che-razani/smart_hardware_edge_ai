#include "ultrasonic.h"
#include <Arduino.h>
#include "config.h"
namespace {
uint32_t lastPing = 0, lastUpdate = 0;
uint16_t reading = 0;
bool valid = false;
}
namespace ultrasonic {
void begin() {
    pinMode(sentinel::kUltrasonicTrig, OUTPUT);
    pinMode(sentinel::kUltrasonicEcho, INPUT);
    digitalWrite(sentinel::kUltrasonicTrig, LOW);
}
void poll(uint32_t now) {
    if (uint32_t(now - lastPing) < sentinel::kUltrasonicIntervalMs) return;
    lastPing = now;
    digitalWrite(sentinel::kUltrasonicTrig, LOW); delayMicroseconds(2);
    digitalWrite(sentinel::kUltrasonicTrig, HIGH); delayMicroseconds(10);
    digitalWrite(sentinel::kUltrasonicTrig, LOW);
    uint32_t echo = pulseIn(sentinel::kUltrasonicEcho, HIGH, sentinel::kUltrasonicTimeoutUs);
    if (echo == 0) { valid = false; return; } // No echo within timeout: out of range or missing sensor.
    // 343 m/s speed of sound; round-trip halved for one-way distance, result in millimetres.
    reading = static_cast<uint16_t>((echo * 343UL) / 2000UL);
    lastUpdate = now;
    valid = true;
}
bool value(uint16_t& mm, uint32_t& updated) {
    mm = reading; updated = lastUpdate; return valid;
}
}
