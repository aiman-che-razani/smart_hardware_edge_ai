#pragma once

#include <stdint.h>

namespace sentinel {
constexpr uint32_t kConsoleBaud = 115200UL;
constexpr uint16_t kReportIntervalMs = 1000;      // One assembled DATA frame per second.
constexpr uint16_t kUltrasonicIntervalMs = 150;   // HC-SR04 needs >=60 ms between pings; margin.
constexpr uint32_t kUltrasonicTimeoutUs = 25000;  // ~4.3 m max range at 343 m/s round trip.
constexpr uint16_t kAmbientIntervalMs = 2000;     // Covers both DHT11 (1 s) and DHT22 (2 s) minimums.
constexpr uint8_t kUltrasonicEcho = 2, kUltrasonicTrig = 3;
constexpr uint8_t kAmbientData = 4;
constexpr uint8_t kGreen = 5, kAmber = 6, kRed = 7, kBuzzer = 8;  // Buzzer driven via PN2222.
constexpr uint16_t kBuzzerHz = 2500;  // Passive piezo: needs an oscillating tone(), not a static HIGH.
constexpr uint8_t kWaterLevelPin = 14, kThermistorPin = 15, kLightPin = 16;  // A0, A1, A2.
}  // namespace sentinel
