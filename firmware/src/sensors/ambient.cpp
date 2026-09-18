#include "ambient.h"
#include <Arduino.h>
#include <SimpleDHT.h>
#include "config.h"
namespace {
// DHT11 by default (whole-degree/whole-percent readings); swap for SimpleDHT22
// and remove the *10 scaling below if the fitted module is a DHT22 instead —
// confirm against the physical part's markings before wiring.
SimpleDHT11 sensor(sentinel::kAmbientData);
uint32_t lastRead = 0, lastUpdate = 0;
int16_t temperature = 0;
uint16_t humidity = 0;
bool valid = false, checksumError = false;
}
namespace ambient {
void begin() {}
void poll(uint32_t now) {
    if (uint32_t(now - lastRead) < sentinel::kAmbientIntervalMs) return;
    lastRead = now;
    byte wholeTemp = 0, wholeHumidity = 0;
    int err = sensor.read(&wholeTemp, &wholeHumidity, nullptr);
    if (err != SimpleDHTErrSuccess) {
        valid = false;
        checksumError = (err == SimpleDHTErrDataChecksum);
        return;
    }
    checksumError = false;
    temperature = int16_t(wholeTemp) * 10;   // whole degrees C -> deci-C
    humidity = uint16_t(wholeHumidity) * 10; // whole percent RH -> deci-%RH
    valid = true;
    lastUpdate = now;
}
bool value(int16_t& tempTenthsC, uint16_t& humidityTenthsPct, uint32_t& updated) {
    tempTenthsC = temperature; humidityTenthsPct = humidity; updated = lastUpdate;
    return valid;
}
bool checksumFailed() { return checksumError; }
}
