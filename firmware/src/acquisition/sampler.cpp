#include "sampler.h"
#include "../sensors/ultrasonic.h"
#include "../sensors/water_level.h"
#include "../sensors/ambient.h"
#include "../sensors/analog_environment.h"
#include "../communication/serial_protocol.h"
#include "types.h"
#include "config.h"
#include <Arduino.h>
namespace {
Sample sample = {};
uint32_t lastReport = 0, lastStatus = 0;
uint16_t age(uint32_t now, uint32_t previous) {
    uint32_t elapsed = now - previous;
    return elapsed > 65535 ? 65535 : uint16_t(elapsed);
}
}
namespace sampler {
void begin(uint32_t boot) {
    sample.boot = boot;
    ultrasonic::begin();
    waterLevel::begin();
    ambient::begin();
    analogEnvironment::begin();
}
void poll() {
    uint32_t now = millis();
    ultrasonic::poll(now);
    ambient::poll(now);
    if (uint32_t(now - lastStatus) >= 1000) { lastStatus = now; transport::status(); }
    if (uint32_t(now - lastReport) < sentinel::kReportIntervalMs) return;
    lastReport = now;

    uint16_t distance = 0; uint32_t distanceTime = 0;
    bool distanceOk = ultrasonic::value(distance, distanceTime);
    int16_t ambientTemp = 0; uint16_t ambientHumidity = 0; uint32_t ambientTime = 0;
    bool ambientOk = ambient::value(ambientTemp, ambientHumidity, ambientTime);

    sample.timestamp = now;
    sample.distance = distance;
    sample.distanceAge = age(now, distanceTime);
    sample.waterLevel = waterLevel::read();
    sample.thermistor = analogEnvironment::thermistor();
    sample.light = analogEnvironment::light();
    sample.ambientTemperature = ambientTemp;
    sample.ambientHumidity = ambientHumidity;
    sample.ambientAge = age(now, ambientTime);
    // Bit 1 = distance valid, bit 2 = ambient (DHT) valid, bit 4 = DHT checksum error.
    sample.flags = (distanceOk ? 1 : 0) | (ambientOk ? 2 : 0) | (ambient::checksumFailed() ? 4 : 0);
    ++sample.sequence;
    if (transport::streaming()) transport::send(sample);
}
}
